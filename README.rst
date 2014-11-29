Chest
=====

|Build Status| |Coverage Status| |Version Status| |Downloads|

A dictionary that spills to disk.

Chest acts likes a dictionary but it can write its contents to disk.  This is
useful in the following two occasions:

1.  Chest can hold datasets that are larger than memory
2.  Chest persists and so can be saved and loaded for later use

Related Projects
----------------

The standard library ``shelve`` is an alternative out-of-core dictionary.
``Chest`` offers the following benefits over shelve_:

1.  Chest supports any hashable key (not just strings)
2.  Chest supports pluggable serialization and file saving schemes

Alternatively one might consider a traditional key-value store database like
Redis_.


LICENSE
-------

New BSD. See License_


Install
-------

``chest`` is on the Python Package Index (PyPI):

::

    pip install chest


Example
-------

.. code:: python

    >>> from chest import Chest
    >>> c = Chest()

    >>> # Acts like a normal dictionary
    >>> c['x'] = [1, 2, 3]
    >>> c['x']
    [1, 2, 3]

    >>> # Data persists to local files
    >>> c.flush()
    >>> import os
    >>> os.listdir(c.path)
    ['.keys', 'x']

    >>> # These files hold pickled results
    >>> import pickle
    >>> pickle.load(open(c.path))
    [1, 2, 3]

    >>> # Though one normally accesses these files with chest itself
    >>> c2 = Chest(path=c.path)
    >>> c2.keys()
    ['x']
    >>> c2['x']
    [1, 2, 3]

    >>> # Chest is configurable, so one can use json instead of pickle
    >>> import json
    >>> c = Chest(path='my-chest', dump=json.dump, load=json.load)
    >>> c['x'] = [1, 2, 3]
    >>> c.flush()

    >>> json.load(open('my-chest'))
    [1, 2, 3]


Known Failings
--------------

Chest was designed to hold a moderate amount of largish numpy arrays.  It
doesn't handle the very many small key-value pairs usecase (though could with
small effort).  In particular chest has the following deficiencies

1.  It determines what values to spill to disk by size.  The largest values are
    spilled.  This can be improved by better determination of size (see the
    ``nbytes`` function) and consideration of time-of-use (like an LRU
    mechanism.)
2.  Spill conditions are checked after every action.  Spill conditions often
    involve an ``n log(n)`` sorting process.  This could be improved by
    tracking and efficiently updating the size of all values iteratively.
3.  Chest is not multi-process safe.  We should institute a file lock at least
    around the ``.keys`` file.
4.  Chest does not support mutation of variables on disk.


Dependencies
------------

``Chest`` supports Python 2.6+ and Python 3.2+ with a common codebase.
It is pure Python and requires no dependencies beyond the standard
library.

It is, in short, a light weight dependency.

Author
------

Chest was originally created by `Matthew Rocklin`_

.. _`Matthew Rocklin`: http://matthewrocklin.com
.. _shelve: https://docs.python.org/3/library/shelve.html
.. _License: https://github.com/mrocklin/chest/blob/master/LICENSE.txt
.. _Redis: http://redis.io/
.. |Build Status| image:: https://travis-ci.org/mrocklin/chest.png
   :target: https://travis-ci.org/mrocklin/chest
.. |Coverage Status| image:: https://coveralls.io/repos/mrocklin/chest/badge.png
   :target: https://coveralls.io/r/mrocklin/chest
.. |Version Status| image:: https://pypip.in/v/chest/badge.png
   :target: https://pypi.python.org/pypi/chest/
.. |Downloads| image:: https://pypip.in/d/chest/badge.png
   :target: https://pypi.python.org/pypi/chest/
