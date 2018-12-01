import unittest


class TestMurmurhash(unittest.TestCase):

    # This package only exports a Cython API, so it can't be tested in pure Python.
    def test_basic(self):
        import murmurhash.mrmr  # noqa: F401
