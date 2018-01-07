from __future__ import absolute_import, division, print_function

import unittest


class TestSympy(unittest.TestCase):

    def test_basic(self):
        from sympy import symbols
        x = symbols("x")
        expr = (3 * x**2) + (2 * x)
        self.assertEqual(0, expr.subs(x, 0))
        self.assertEqual(5, expr.subs(x, 1))
        self.assertEqual(16, expr.subs(x, 2))
