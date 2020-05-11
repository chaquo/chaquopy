import unittest


class TestLruDict(unittest.TestCase):

    def test_basic(self):
        from lru import LRU
        l = LRU(3)
        l[1] = None
        l[2] = None
        l[3] = None
        l[1]
        l[4] = None
        self.assertEqual([4, 1, 3], l.keys())
