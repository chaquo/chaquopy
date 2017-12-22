from __future__ import absolute_import, division, print_function

from java import jclass
import re

from .test_utils import FilterWarningsCase


class TestException(FilterWarningsCase):

    def setUp(self):
        super(TestException, self).setUp()
        self.TE = jclass('com.chaquo.python.TestException')

    def test_constructor(self):
        from java.lang import RuntimeException
        with self.assertRaisesRegexp(RuntimeException,
                                     r"^hello constructor" + trace_line("<init>")):
            self.TE(True)

    def test_simple(self):
        from java.lang import RuntimeException
        with self.assertRaisesRegexp(RuntimeException,
                                     r"^hello method\s*\n" + trace_line("simple")):
            self.TE.simple(0)

        with self.assertRaisesRegexp(RuntimeException,
                                     (r"^hello method\s*\n" + trace_line("simple") +
                                      trace_line("simple"))):
            self.TE.simple(1)

    def test_chained(self):
        from java.lang import RuntimeException
        with self.assertRaisesRegexp(
                RuntimeException,
                re.compile(r"^2\s*\n" +
                           trace_line("chain2") +
                           r".*Caused by: java.lang.RuntimeException: 1\s*\n" +
                           trace_line("chain1") + trace_line("chain2") +
                           r".*Caused by: java.lang.RuntimeException: hello method\s*\n" +
                           trace_line("simple") + trace_line("chain1"),
                           re.DOTALL)):
            self.TE.chain2()

    def test_catch(self):
        from java.lang import Integer
        from java.lang import RuntimeException, IllegalArgumentException, NumberFormatException
        with self.assertRaises(NumberFormatException):      # Actual class
            Integer.parseInt("hello")
        with self.assertRaises(IllegalArgumentException):   # Parent class
            Integer.parseInt("hello")
        with self.assertRaises(RuntimeException):           # Grandparent class
            Integer.parseInt("hello")

        from java.lang import System
        from java.io import IOException
        try:
            System.getProperty("")
        except IOException:                                 # Unrelated class
            self.fail()
        except NumberFormatException:                       # Child class
            self.fail()
        except IllegalArgumentException:                    # Actual class
            pass


def trace_line(method):
    return (r"\s*at com.chaquo.python.TestException." + method +
            r"\(TestException.java:[0-9]+\)\s*")
