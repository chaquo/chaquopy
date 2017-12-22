from __future__ import absolute_import, division, print_function

from unittest import TestCase
from warnings import catch_warnings, filterwarnings


class FilterWarningsCase(TestCase):

    def setUp(self):
        super(FilterWarningsCase, self).setUp()
        self.cw = catch_warnings()
        self.cw.__enter__()
        filterwarnings("error")
        filterwarnings("ignore", r"Please use assert\w+ instead")

    def tearDown(self):
        self.cw.__exit__(None, None, None)
        super(FilterWarningsCase, self).tearDown()


Object_names = {"clone", "equals", "finalize", "getClass", "hashCode", "notify",
                "notifyAll", "toString", "wait"}

def assertDir(self, obj, expected):
    self.assertEqual(sorted(expected),
                     [s for s in dir(obj) if
                      not (s.startswith("__") or s.startswith("_chaquopy") or
                           s in ["<init>",               # Java constructor
                                 "serialVersionUID"])])  # Android adds this to some classes
