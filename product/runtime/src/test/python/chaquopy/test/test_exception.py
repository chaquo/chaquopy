from java import jclass
import re

from .test_utils import FilterWarningsCase


class TestException(FilterWarningsCase):

    def setUp(self):
        super().setUp()
        self.TE = jclass('com.chaquo.python.TestException')

    def test_constructor(self):
        from java.lang import RuntimeException
        with self.assertRaisesRegex(RuntimeException,
                                    r"^hello constructor\s*\n" + trace_line("<init>")):
            self.TE(True)

    def test_simple(self):
        from java.lang import RuntimeException
        with self.assertRaisesRegex(RuntimeException,
                                    r"^hello method\s*\n" + trace_line("simple")):
            self.TE.simple(0)

        with self.assertRaisesRegex(RuntimeException,
                                    (r"^hello method\s*\n" + trace_line("simple") +
                                     trace_line("simple"))):
            self.TE.simple(1)

    def test_chained(self):
        from java.lang import RuntimeException
        with self.assertRaisesRegex(
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
    # With AGP 8.2, ProGuard obfuscates Java source filenames even when the class name
    # itself is visible, so we can't check them.
    #
    # With AGP 9.0, ProGuard causes an "androidx.core.app.c.p" frame to appear at the
    # top of the stack trace. So we allow one additional line before the expected line.
    return (r"(.*\n)?\s*at com.chaquo.python.TestException." + method +
            r"\(.+:[0-9]+\)\s*")
