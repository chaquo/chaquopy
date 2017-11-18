import unittest

class TestNumpy(unittest.TestCase):

    def test_basic(self):
        from numpy import array
        self.assertEqual([4,7], (array([1,2]) + array([3,5])).tolist())
