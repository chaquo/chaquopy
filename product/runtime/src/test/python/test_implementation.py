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

        # TODO #5181 This should be implemented in JavaObject.__new__, using identityHashCode
        # followed by IsSameObject. Consider how this will interact with aliases created by
        # `cast`; `is` probably can't say that they're also the same object, but that's not a
        # major problem (document at `cast`). Test garbage collection just like in the Java
        # unit tests.
        #
        # self.assertIs(System.out, System.out)

        self.assertEqual(False, System.out.checkError())
        self.assertIsNone(System.out.flush())

    def test_unconstructible(self):
        System = autoclass("java.lang.System")
        with self.assertRaisesRegexp(TypeError, "no accessible constructors"):
            System()

    def test_unicode(self):
        String = autoclass('java.lang.String')
        self.assertEqual(u'é', String.format(u'é'))

        # Null character (handled differently by "modified UTF-8")
        self.assertEqual(u'A\u0000B', String.format(u'A\u0000B'))

        # Non-BMP character (handled differently by "modified UTF-8")
        self.assertEqual(u'A\U00012345B', String.format(u'A\U00012345B'))

    def test_reserved_words(self):
        StringWriter = autoclass("java.io.StringWriter")
        PrintWriter = autoclass("java.io.PrintWriter")
        self.assertIs(PrintWriter.__dict__["print"], PrintWriter.__dict__["print_"])
        sw = StringWriter()
        pw = PrintWriter(sw)
        self.assertTrue(hasattr(pw, "print_"))
        self.assertFalse(hasattr(pw, "flush_"))
        pw.print_("Hello")
        pw.print_(" world")
        self.assertEqual("Hello world", sw.toString())
