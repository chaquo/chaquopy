import unittest


class TestEphem(unittest.TestCase):

    def test_basic(self):
        import ephem
        u = ephem.Uranus()
        u.compute("1781/3/13")
        self.assertEqual("5:35:45.28", str(u.ra))
