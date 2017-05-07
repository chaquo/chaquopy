from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest
from chaquopy.reflect import autoclass

class MultipleSignature(unittest.TestCase):

    def test_multiple_constructors(self):
        String = autoclass('java.lang.String')
        self.assertIsNotNone(String('Hello World'))
        self.assertIsNotNone(String(list('Hello World')))
        self.assertIsNotNone(String(list('Hello World'), 3, 5))

    def test_multiple_methods(self):
        String = autoclass('java.lang.String')
        s = String('hello')
        self.assertEquals(s.getBytes(), [104, 101, 108, 108, 111])
        self.assertEquals(s.getBytes('utf8'), [104, 101, 108, 108, 111])
        self.assertEquals(s.indexOf(ord('e')), 1)
        self.assertEquals(s.indexOf(ord('e'), 2), -1)

    def test_multiple_methods_no_args(self):
        MultipleMethods = autoclass('com.chaquo.python.MultipleMethods')
        self.assertEqual(MultipleMethods.resolve(), 'resolved no args')

    def test_multiple_methods_one_arg(self):
        MultipleMethods = autoclass('com.chaquo.python.MultipleMethods')
        self.assertEqual(MultipleMethods.resolve('arg'), 'resolved one arg')

    def test_multiple_methods_two_args(self):
        MultipleMethods = autoclass('com.chaquo.python.MultipleMethods')
        self.assertEqual(MultipleMethods.resolve('one', 'two'), 'resolved two args')

    def test_multiple_methods_two_string_and_an_integer(self):
        MultipleMethods = autoclass('com.chaquo.python.MultipleMethods')
        self.assertEqual(MultipleMethods.resolve('one', 'two', 1), 'resolved two string and an integer')

    def test_multiple_methods_two_string_and_two_integers(self):
        MultipleMethods = autoclass('com.chaquo.python.MultipleMethods')
        self.assertEqual(MultipleMethods.resolve('one', 'two', 1, 2), 'resolved two string and two integers')

    def test_multiple_methods_varargs(self):
        MultipleMethods = autoclass('com.chaquo.python.MultipleMethods')
        self.assertEqual(MultipleMethods.resolve(1, 2, 3), 'resolved varargs')

    def test_multiple_methods_two_args_and_varargs(self):
        MultipleMethods = autoclass('com.chaquo.python.MultipleMethods')
        self.assertEqual(MultipleMethods.resolve('one', 'two', 1, 2, 3), 'resolved two args and varargs')

    # FIXME static, and mixed static/non-static (Java pays no attention to static-ness when
    # deciding overload resolution).

    # TODO the most-derived override of each overload is considered when resolving overloads;
    # position in the class hierarchy does not otherwise affect priority. So if recreating the
    # Java class hierarchy in Python, derived classes will have to provide a JavaMultipleMethod
    # which incorporates all the methods of the same name in all the base classes, unless the
    # derived overload set for that name is identical to that of one of the bases, in which
    # case the usual Python inheritance mechanism can be used.
    #
    # Java doesn't allow overloads (as opposed to overrides) added in derived classes to be
    # called (or even visible) through a base class interface. If the user wants to reproduce
    # this behaviour, they'll have to use the cast() function, otherwise the object's actual
    # class will be used.
