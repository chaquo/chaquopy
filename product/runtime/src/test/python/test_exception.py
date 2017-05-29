from __future__ import absolute_import, division, print_function

import re
import unittest

from java import *


class TestException(unittest.TestCase):

    def setUp(self):
        self.TE = jclass('com.chaquo.python.TestException')

    def test_constructor(self):
        with self.assertRaisesRegexp(JavaException, "java.lang.RuntimeException: hello"):
            self.TE(True)

    def test_simple(self):
        with self.assertRaisesRegexp(JavaException, (r"^java.lang.RuntimeException: hello world\s*\n" +
                                                     trace_line("simple") + "$")):
            self.TE.simple(0)

        with self.assertRaisesRegexp(JavaException, (r"^java.lang.RuntimeException: hello world\s*\n" +
                                                     trace_line("simple") + trace_line("simple") + "$")):
            self.TE.simple(1)

    def test_chained(self):
        with self.assertRaisesRegexp(JavaException, (r"^java.lang.RuntimeException: 2\s*\n" +
                                                     trace_line("chain2") +
                                                     r"Caused by: java.lang.RuntimeException: 1\s*\n" +
                                                     trace_line("chain1") + trace_line("chain2") +
                                                     r"Caused by: java.lang.RuntimeException: hello world\s*\n" +
                                                     trace_line("simple") + trace_line("chain1") +
                                                     "\s*... 1 more")):
            self.TE.chain2()


def trace_line(method):
    return (r"\s*at com.chaquo.python.TestException." + method +
            r"\(TestException.java:[0-9]+\)\s*\n")
