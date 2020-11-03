from contextlib import contextmanager
from time import time
from unittest import TestCase
from warnings import catch_warnings, filterwarnings


try:
    from android.os import Build
except ImportError:
    API_LEVEL = None
else:
    API_LEVEL = Build.VERSION.SDK_INT


# Make warnings fatal.
class FilterWarningsCase(TestCase):

    def setUp(self):
        super().setUp()
        self.cw = catch_warnings()
        self.cw.__enter__()
        filterwarnings("error")

    def tearDown(self):
        self.cw.__exit__(None, None, None)
        super().tearDown()


Object_names = {"clone", "equals", "finalize", "getClass", "hashCode", "notify",
                "notifyAll", "toString", "wait"}

def assertDir(self, obj, expected):
    self.assertEqual(sorted(expected),
                     [s for s in dir(obj) if
                      not (s.startswith("__") or s.startswith("_chaquopy") or
                           s in ["<init>",               # Java constructor
                                 "serialVersionUID"])])  # Android adds this to some classes


@contextmanager
def assertTimeLimit(self, limit):
    start = time()
    yield
    self.assertLess(time() - start, limit)
