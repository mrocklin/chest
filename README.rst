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
