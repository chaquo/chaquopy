import unittest


class TestPreshed(unittest.TestCase):

    # Based on https://github.com/explosion/preshed/blob/master/preshed/tests/test_hashing.py
    def test_basic(self):
        from preshed.maps import PreshMap
        h = PreshMap()
        self.assertIsNone(h[1])
        h[1] = 5
        self.assertEqual(5, h[1])
        h[2] = 6
        self.assertEqual(5, h[1])
        self.assertEqual(6, h[2])
        h[1] = 7
        self.assertEqual(7, h[1])
        self.assertEqual(6, h[2])
