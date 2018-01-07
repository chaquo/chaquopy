from __future__ import absolute_import, division, print_function

import unittest


class TestMpmath(unittest.TestCase):

    def test_basic(self):
        from mpmath import mp, pi
        mp.dps = 30
        self.assertEqual("3.14159265358979323846264338328", str(pi))
