import unittest


class TestCytoolz(unittest.TestCase):

    def test_basic(self):
        from cytoolz import frequencies
        self.assertEqual({'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1},
                         frequencies("abracadabra"))
