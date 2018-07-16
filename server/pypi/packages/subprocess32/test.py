from __future__ import absolute_import, division, print_function

import unittest


class TestSubprocess32(unittest.TestCase):

    # Minimal import test
    def test_basic(self):
        import subprocess32
        import sys

        self.assertEqual(sys.version_info[0] < 3,
                         "_posixsubprocess32" in sys.modules)
        self.assertTrue(hasattr(subprocess32, "run"))
