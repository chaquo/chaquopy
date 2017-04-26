from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest
from chaquopy.reflect import autoclass

class BasicsTest(unittest.TestCase):

    def test_static_methods(self):
        ClassArgument = autoclass('com.chaquo.python.ClassArgument')
        self.assertEquals(ClassArgument.getName(ClassArgument), 'class com.chaquo.python.ClassArgument')
