from __future__ import absolute_import, division, print_function

import unittest


class TestTwisted(unittest.TestCase):

    def test_basic(self):
        # This is the only native module. It's for unit test purposes only, but the package
        # build still requires it.
        from twisted.test import raiser
        with self.assertRaises(raiser.RaiserException):
            raiser.raiseException()
