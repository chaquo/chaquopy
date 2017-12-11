from __future__ import absolute_import, division, print_function

import unittest

from java import jclass


# The full Java API is tested by the Java unit tests, but this covers some specific
# interactions between the Python and Java modules.
class TestJavaAPI(unittest.TestCase):

    # Test that the `java` module calls Python.start() during initialization. This test must
    # run first, or getInstance() will call start() itself.
    def test_0_start(self):
        Python = jclass("com.chaquo.python.Python")
        self.assertTrue(Python.isStarted())

    def test_pyobject(self):
        Python = jclass("com.chaquo.python.Python")
        self.assertIs(unittest, Python.getInstance().getModule("unittest"))
