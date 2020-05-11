import unittest


class TestScipy(unittest.TestCase):

    def test_interpolate(self):
        import numpy as np
        from scipy.interpolate import griddata
        points = [[0, 0], [1, 0], [0, 1]]
        values = [1, 2, 3]
        np.testing.assert_allclose(
            [1, 1.5, 2, 2.5, 3],
            griddata(points, values, [[0, 0], [0.5, 0], [1, 0], [0.5, 0.5], [0, 1]]))
        np.testing.assert_allclose(
            [1.3, 1.7, 2.1, 2.5, np.nan],
            griddata(points, values, [[0.3, 0], [0.3, 0.2], [0.3, 0.4], [0.3, 0.6], [0.3, 0.8]]),
            equal_nan=True)

    def test_optimize(self):
        from scipy.optimize import minimize
        def f(x):
            return (x - 42) ** 2
        self.assertEqual(42, round(minimize(f, [123]).x[0]))
