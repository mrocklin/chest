from collections import MutableMapping
from functools import partial
from threading import Lock
import sys
import tempfile
import shutil
import os
import re
import pickle
from heapdict import heapdict
import hashlib

DEFAULT_AVAILABLE_MEMORY = 1e9


def key_to_filename(key):
    """ Return a filename from any kind of hashable key

    >>> type(key_to_filename(('foo', 'bar'))).__name__
    'str'
    """
    if isinstance(key, str) and re.match('^[_a-zA-Z]\w*$', key):
        return key
    if isinstance(key, tuple):
        names = (['_' + key_to_filename(k) for k in key[:-1]] +
                 [key_to_filename(key[-1])])
        return os.path.join(*names)
    else:
        return str(hashlib.md5(str(key).encode()).hexdigest())


def _do_nothing(*args, **kwargs):
    pass


class Chest(MutableMapping):
    """ A Dictionary that spills to disk

    Chest acts like a normal Python dictionary except that it writes large
    contents to disk.  It is ideal to store and access collections of large
    variables like arrays.

    Paramters
    ---------

    data : dict (optional)
        An initial dictionary to seed the chest
    path : str (optional)
        A directory path to store contents of the chest.  Defaults to a tmp dir
    available_memory : int (optional)
        Number of bytes that a chest should use for in-memory storage
    dump : function (optional)
        A function like pickle.dump or json.dump that dumps contents to file
    load : function(optional)
        A function like pickle.load or json.load that loads contents from file
    key_to_filename : function (optional)
        A function to determine filenames from key values
    mode : str (t or b)
        Binary or text mode for file storage

    Examples
    --------

    >>> c = Chest(path='my-chest')
    >>> c['x'] = [1, 2, 3]
    >>> c['x']
    [1, 2, 3]

    >>> c.flush()
    >>> import os
    >>> sorted(os.listdir(c.path))
    ['.keys', 'x']

    >>> c.drop()
    """
    def __init__(self, data=None, path=None, available_memory=None,
                 dump=partial(pickle.dump, protocol=1),
                 load=pickle.load,
                 key_to_filename=key_to_filename,
                 on_miss=_do_nothing, on_overflow=_do_nothing,
                 mode='b'):
        # In memory storage
        self.inmem = data or dict()
        # A set of keys held both in memory or on disk
        self._keys = {}
        # Was a path given or no?  If not we'll clean up the directory later
        self._explicitly_given_path = path is not None
        # Diretory where the on-disk data will be held
        self.path = path or tempfile.mkdtemp('.chest')
        if not os.path.exists(self.path):
            os.mkdir(self.path)
        # Amount of memory we're allowed to use
        self.available_memory = (available_memory if available_memory
                                 is not None else DEFAULT_AVAILABLE_MEMORY)
        # Functions to control disk I/O
        self.load = load
        self.dump = dump
        self.mode = mode
        self._key_to_filename = key_to_filename

        keyfile = os.path.join(self.path, '.keys')
        if os.path.exists(keyfile):
            with open(keyfile, mode='r'+self.mode) as f:
                self._keys = dict(self.load(f))

        self.lock = Lock()

        # LRU state
        self.counter = 0
        self.heap = heapdict()

        # Debug
        self._on_miss = on_miss
        self._on_overflow = on_overflow

    def __str__(self):
        return '<chest at %s>' % self.path

    def key_to_filename(self, key):
        """ Filename where key will be held """
        if key in self._keys:
            return os.path.join(self.path, self._keys[key])
        else:
            return os.path.join(self.path, self._key_to_filename(key))

    def move_to_disk(self, key):
        """ Move data from memory onto disk """
        self._on_overflow(key)
        fn = self.key_to_filename(key)
        if not os.path.exists(fn):  # Only write if it doesn't exist.
            dir = os.path.dirname(fn)
            if not os.path.exists(dir):
                os.makedirs(dir)
            try:
                with open(fn, mode='w'+self.mode) as f:
                    self.dump(self.inmem[key], f)
            except TypeError:
                os.remove(fn)
                raise
        del self.inmem[key]

    def get_from_disk(self, key):
        """ Pull value from disk into memory """
        if key in self.inmem:
            return

        self._on_miss(key)

        fn = self.key_to_filename(key)
        with open(fn, mode='r'+self.mode) as f:
            value = self.load(f)

        self.inmem[key] = value

    def __getitem__(self, key):
        with self.lock:
            if key in self.inmem:
                value = self.inmem[key]
            else:
                if key not in self._keys:
                    raise KeyError("Key not found: %s" % key)

                self.get_from_disk(key)
                value = self.inmem[key]
                self._update_lru(key)

        with self.lock:
            self.shrink()

        return value

    def _update_lru(self, key):
        self.counter += 1
        self.heap[key] = self.counter

    def __delitem__(self, key):
        if key in self.inmem:
            del self.inmem[key]
        if key in self.heap:
            del self.heap[key]

        fn = self.key_to_filename(key)
        if os.path.exists(fn):
            os.remove(fn)

        del self._keys[key]

    def __setitem__(self, key, value):
        with self.lock:
            if key in self._keys:
                del self[key]

            self.inmem[key] = value
            self._keys[key] = self._key_to_filename(key)
            self._update_lru(key)

        with self.lock:
            self.shrink()

    def __del__(self):
        if self._explicitly_given_path:
            if os.path.exists(self.path):
                self.flush()
            else:
                with self.lock:
                    for key in list(self.inmem):
                        del self.inmem[key]
        elif os.path.exists(self.path):
            with self.lock:
                self.drop()  # pragma: no cover

    def __iter__(self):
        return iter(self._keys)

    def __len__(self):
        return len(self._keys)

    def __contains__(self, key):
        return key in self._keys

    @property
    def memory_usage(self):
        result = sum(map(nbytes, self.inmem.values()))
        return result

    def shrink(self):
        """
        Spill in-memory storage to disk until usage is less than available

        Just implemented with "dump the biggest" for now.  This could be
        improved to LRU or some such.  Ideally this becomes an input.
        """
        mem = self.memory_usage
        if mem < self.available_memory:
            return

        while mem > self.available_memory:
            key, _ = self.heap.popitem()
            data = self.inmem[key]
            try:
                self.move_to_disk(key)
                mem -= nbytes(data)
            except TypeError:
                pass

    def drop(self):
        """ Permanently remove directory from disk """
        shutil.rmtree(self.path)

    def write_keys(self):
        fn = os.path.join(self.path, '.keys')
        with open(fn, mode='w'+self.mode) as f:
            self.dump(list(self._keys.items()), f)

    def flush(self):
        """ Flush all in-memory storage to disk """
        with self.lock:
            for key in list(self.inmem):
                self.move_to_disk(key)
            self.write_keys()

    def __enter__(self):
        return self

    def __exit__(self, eType, eValue, eTrace):
        with self.lock:
            L = os.listdir(self.path)
            if not self._explicitly_given_path and os.path.exists(self.path):
                self.drop()  # pragma: no cover

        if eValue is not None:
            if not isinstance(eValue, Exception):  # Py26 behavior
                eValue = eType(eValue)  # pragma: no cover
            raise eValue

    def update(self, other, overwrite=True):
        """ Copy (hard-link) the contents of chest other to this chest """
        #  if already flushed, then this does nothing
        self.flush()
        other.flush()
        for key in other._keys:
            if key in self._keys and overwrite:
                del self[key]
            elif key in self._keys and not overwrite:
                continue
            old_fn = other.key_to_filename(key)
            self._keys[key] = self._key_to_filename(key)
            new_fn = self.key_to_filename(key)
            dir = os.path.dirname(new_fn)
            if not os.path.exists(dir):
                os.makedirs(dir)
            os.link(old_fn, new_fn)


def nbytes(o):
    """ Number of bytes of an object

    >>> nbytes(123)  # doctest: +SKIP
    24

    >>> nbytes('Hello, world!')  # doctest: +SKIP
    50

    >>> import numpy as np
    >>> nbytes(np.ones(1000, dtype='i4'))
    4000
    """
    if hasattr(o, 'nbytes'):
        return o.nbytes
    if hasattr(o, 'values') and hasattr(o, 'index'):
        return o.values.nbytes + o.index.nbytes  # pragma: no cover
    else:
        return sys.getsizeof(o)
