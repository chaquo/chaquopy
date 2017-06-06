from __future__ import absolute_import, division, print_function

import re
from unittest import TestCase

from java import *


class TestException(TestCase):

    arr = TestCase.assertRaisesRegexp

    def setUp(self):
        self.TE = jclass('com.chaquo.python.TestException')

    def test_constructor(self):
        with self.arr(JavaException, "java.lang.RuntimeException: hello"):
            self.TE(True)

    def test_simple(self):
        with self.arr(JavaException, (r"^java.lang.RuntimeException: hello world\s*\n" +
                                      trace_line("simple"))):
            self.TE.simple(0)

        with self.arr(JavaException, (r"^java.lang.RuntimeException: hello world\s*\n" +
                                      trace_line("simple") + trace_line("simple"))):
            self.TE.simple(1)

    def test_chained(self):
        with self.arr(JavaException,
                      re.compile(r"^java.lang.RuntimeException: 2\s*\n" +
                                 trace_line("chain2") +
                                 r".*Caused by: java.lang.RuntimeException: 1\s*\n" +
                                 trace_line("chain1") + trace_line("chain2") +
                                 r".*Caused by: java.lang.RuntimeException: hello world\s*\n" +
                                 trace_line("simple") + trace_line("chain1"),
                                 re.DOTALL)):
            self.TE.chain2()


def trace_line(method):
    return (r"\s*at com.chaquo.python.TestException." + method +
            r"\(TestException.java:[0-9]+\)\s*\n")
