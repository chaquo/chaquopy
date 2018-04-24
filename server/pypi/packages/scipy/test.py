from __future__ import absolute_import, division, print_function

import unittest


class TestScipy(unittest.TestCase):

    def test_optimize(self):
        from scipy.optimize import minimize
        def f(x):
            return (x - 42) ** 2
        self.assertEqual(42, round(minimize(f, [123]).x[0]))
