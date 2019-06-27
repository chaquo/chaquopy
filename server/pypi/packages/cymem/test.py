import unittest


class TestCymem(unittest.TestCase):

    # This package can only be tested properly from Cython, but do some basic sanity checks.
    def test_basic(self):
        from cymem.cymem import Pool
        p = Pool()
        self.assertEqual(0, p.size)
