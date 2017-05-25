from __future__ import absolute_import, division, print_function

import unittest

from chaquopy import *


# The full Java API is tested by the Java unit tests, but this covers some specific
# interactions between the Python and Java modules.
class TestJavaAPI(unittest.TestCase):

    # Any use of the Python module should set a flag preventing the Java module from trying to
    # start Python.
    def test_start(self):
        Python = jclass("com.chaquo.python.Python")
        self.assertTrue(Python.isStarted())
        with self.assertRaisesRegexp(JavaException, "already started"):
            Python.start(None)

    def test_pyobject(self):
        Python = jclass("com.chaquo.python.Python")
        self.assertIs(unittest, Python.getInstance().getModule("unittest"))
