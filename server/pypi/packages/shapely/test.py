import unittest


class TestShapely(unittest.TestCase):

    def test_basic(self):
        from shapely.geometry import Point
        patch = Point(0.0, 0.0).buffer(10.0)
        self.assertAlmostEqual(313.65, patch.area, places=2)

        from shapely import speedups
        self.assertTrue(speedups.enabled)

        from shapely import vectorized
        self.assertEqual([False, True, True, False],
                         vectorized.contains(patch,
                                             [11, 9, -7, -8],
                                             [0,  0,  7,  7]).tolist())
