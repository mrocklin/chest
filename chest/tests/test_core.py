from chest.core import Chest, nbytes
import os
import pickle
from contextlib import contextmanager
import numpy as np
from chest.utils import raises


@contextmanager
def tmp_chest(*args, **kwargs):
    c = Chest(*args, **kwargs)

    try:
        yield c
    finally:
        if os.path.exists(c.path):
            c.drop()
        del c


def test_basic():
    with tmp_chest() as c:
        c[1] = 'one'
        c['two'] = 2

        assert c[1] == 'one'
        assert c['two'] == 2
        assert c.path

        assert len(c) == 2
        assert set(c) == set([1, 'two'])


def test_paths():
    with tmp_chest() as c:
        assert os.path.exists(c.path)

        c[1] = 'one'

        c.move_to_disk(1)

        assert os.path.exists(c.key_to_filename(1))

        with open(c.key_to_filename(1), mode='rb') as f:
            assert pickle.load(f) == 'one'


def eq(a, b):
    c = a == b
    if isinstance(c, np.ndarray):
        return c.all()
    return c


def test_limited_storage():
    x = np.ones(1000, dtype='i4')
    y = np.ones(2000, dtype='i4')
    with tmp_chest(available_memory=5000) as c:
        c['x'] = x
        c['y'] = y
        assert c.memory_usage < c.available_memory
        assert 'x' in c
        assert 'y' in c

        assert len(c.inmem) == 1

        assert 'x' in c.inmem
        assert 'y' not in c.inmem

        assert eq(c['x'], x)
        assert eq(c['y'], y)


def test_limited_shrink_called_normally():
    x = np.ones(1000, dtype='i4')
    y = 2 * np.ones(1000, dtype='i4')
    with tmp_chest(available_memory=0) as c:
        c['x'] = x
        c['y'] = y

        assert not c.inmem

        assert eq(c['x'], x)

        assert not c.inmem


def test_drop():
    with tmp_chest() as c:
        c.drop()
        assert not os.path.exists(c.path)


def test_flush():
    with tmp_chest() as c:
        c[1] = 'one'
        c[2] = 'two'
        c.flush()
        assert os.path.exists(c.key_to_filename(1))
        assert os.path.exists(c.key_to_filename(2))


def test_keys_values_items():
    with tmp_chest() as c:
        c[1] = 'one'
        c[2] = 'two'

        assert set(c.keys()) == set([1, 2])
        assert set(c.values()) == set(['one', 'two'])
        assert set(c.items()) == set([(1, 'one'), (2, 'two')])


def test_recreate_chest():
    with tmp_chest() as c:
        c[1] = 'one'
        c[2] = 'two'

        c.flush()

        c2 = Chest(path=c.path)

        assert c.items() == c2.items()


def test_delitem():
    with tmp_chest() as c:
        c[1] = 'one'
        c[2] = 'two'

        del c[1]

        assert 1 not in c

        c.flush()
        assert 2 in c

        assert os.path.exists(c.key_to_filename(2))
        del c[2]
        assert not os.path.exists(c.key_to_filename(2))


def test_str():
    with tmp_chest() as c:
        assert c.path in str(c)


def test_get_from_disk():
    with tmp_chest() as c:
        c[1] = 'one'  # 1 is in memory
        c.get_from_disk(1)  # shouldn't have an effect
        assert 1 in c.inmem


def test_errors():
    with tmp_chest() as c:
        assert raises(KeyError, lambda: c[1])


def test_reset_item_is_consistent():
    with tmp_chest() as c:
        c[1] = 'one'
        c.flush()

        c[1] = 'uno'
        assert c[1] == 'uno'

        fn = c.key_to_filename(1)

        assert not os.path.exists(fn) or c.load(open(fn)) == 'uno'


def test_nbytes():
    assert isinstance(nbytes('x'), int)
    assert nbytes('x') < 100
    assert nbytes(np.ones(1000, dtype='i4')) >= 4000
