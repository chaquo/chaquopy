# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest
from chaquopy.reflect import autoclass


class ImplementationTest(unittest.TestCase):

    def test_out(self):
        # System.out implies recursive lookup and instantiation of the PrintWriter proxy class.
        System = autoclass('java.lang.System')
        # FIXME self.assertIs(System.out, System.out)
        self.assertEqual(False, System.out.checkError())
        self.assertIsNone(System.out.flush())

    def test_unicode(self):
        String = autoclass('java.lang.String')
        self.assertEqual(u'é', String.format(u'é'))

        # Null character (handled differently by "modified UTF-8")
        self.assertEqual(u'A\u0000B', String.format(u'A\u0000B'))

        # Non-BMP character (handled differently by "modified UTF-8")
        self.assertEqual(u'A\U00012345B', String.format(u'A\U00012345B'))
