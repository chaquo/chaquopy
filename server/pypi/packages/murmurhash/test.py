import unittest


class TestMurmurhash(unittest.TestCase):

    # This package only exports a Cython API, so it can't be tested in pure Python.
    def test_basic(self):
        from murmurhash import mrmr
        self.assertIn("hash32", mrmr.__pyx_capi__)
