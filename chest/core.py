from collections import MutableMapping
from functools import partial
import sys
import tempfile
import shutil
import os
import pickle


def key_to_filename(key):
    """ Return a filename from any kind of hashable key

    >>> type(key_to_filename(('foo', 'bar'))).__name__
    'str'
    """
    if isinstance(key, str):
        return key
    else:
        return str(abs(hash(key)))


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
                 dump=partial(pickle.dump, protocol=2),
                 load=pickle.load,
                 key_to_filename=key_to_filename):
        self.inmem = data or dict()
        self._keys = set()
        self.path = path or tempfile.mkdtemp('chest')[1]
        self.available_memory = (available_memory if available_memory
                                 is not None else 1e9)
        self.load = load
        self.dump = dump
        self._key_to_filename = key_to_filename

        if os.path.exists(self.path):
            fn = os.path.join(self.path, '.keys')
            with open(fn, mode='rb') as f:
                self._keys = self.load(f)
        else:
            os.mkdir(self.path)

    def __str__(self):
        return '<chest at %s>' % self.path

    def key_to_filename(self, key):
        """ Filename where key will be held """
        return os.path.join(self.path, self._key_to_filename(key))

    def move_to_disk(self, key):
        """ Move data from memory onto disk """
        fn = self.key_to_filename(key)
        with open(fn, mode='wb') as f:
            self.dump(self.inmem[key], f)
        del self.inmem[key]

    def get_from_disk(self, key):
        """ Pull value from disk into memory """
        if key in self.inmem:
            return

        fn = self.key_to_filename(key)
        with open(fn, mode='rb') as f:
            self.inmem[key] = self.load(f)

    def __getitem__(self, key):
        try:
            return self.inmem[key]
        except:
            pass

        if key not in self._keys:
            raise KeyError("Key not found: %s" % key)

        self.get_from_disk(key)
        result = self.inmem[key]
        self.shrink()
        return result

    def __delitem__(self, key):
        if key in self.inmem:
            del self.inmem[key]

        fn = self.key_to_filename(key)
        if os.path.exists(fn):
            os.remove(fn)

        self._keys.remove(key)

    def __setitem__(self, key, value):
        if key in self._keys:
            del self[key]

        self.inmem[key] = value
        self._keys.add(key)

        self.shrink()

    def __iter__(self):
        return iter(self._keys)

    def __len__(self):
        return len(self._keys)

    def __contains__(self, key):
        return key in self._keys

    @property
    def memory_usage(self):
        return sum(map(nbytes, self.inmem.values()))

    def shrink(self):
        """
        Spill in-memory storage to disk until usage is less than available

        Just implemented with "dump the biggest" for now.  This could be
        improved to LRU or some such.  Ideally this becomes an input.
        """
        mem = self.memory_usage

        if mem < self.available_memory:
            return
        inmem = sorted(self.inmem.items(),
                       key=lambda kv: nbytes(kv[1]))

        while inmem and mem > self.available_memory:
            key, data = inmem.pop()
            self.move_to_disk(key)
            mem -= nbytes(data)

    def drop(self):
        """ Permanently remove directory from disk """
        shutil.rmtree(self.path)

    def write_keys(self):
        fn = os.path.join(self.path, '.keys')
        with open(fn, mode='wb') as f:
            self.dump(self._keys, f)

    def flush(self):
        """ Flush all in-memory storage to disk """
        for key in list(self.inmem):
            self.move_to_disk(key)
        self.write_keys()


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
    try:
        return o.nbytes
    except AttributeError:
        return sys.getsizeof(o)
