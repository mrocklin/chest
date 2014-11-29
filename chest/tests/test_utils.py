from chest.utils import raises


def test_raises():
    assert raises(KeyError, lambda: {}[1])
    assert not raises(KeyError, lambda: {1: 2}[1])
