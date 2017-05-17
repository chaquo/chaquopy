from __future__ import absolute_import, division, print_function
import unittest
from chaquopy import autoclass


class TestOverload(unittest.TestCase):
    def setUp(self):
        self.Overload = autoclass('com.chaquo.python.Overload')

    def test_constructors(self):
        String = autoclass('java.lang.String')
        self.assertEqual("", String())
        self.assertEqual("Hello World", String('Hello World'))
        self.assertEqual("Hello World", String(list('Hello World')))
        self.assertEqual("lo Wo", String(list('Hello World'), 3, 5))

    def test_no_args(self):
        self.assertEqual(self.Overload.resolve1(), 'resolve1()')

    def test_one_arg(self):
        self.assertEqual(self.Overload.resolve1('arg'), 'resolve1(String)')

    def test_two_args(self):
        self.assertEqual(self.Overload.resolve1('one', 'two'), 'resolve1(String, String)')

    def test_two_string_and_an_integer(self):
        self.assertEqual(self.Overload.resolve1('one', 'two', 1), 'resolve1(String, String, int)')

    def test_two_string_and_two_integers(self):
        self.assertEqual(self.Overload.resolve1('one', 'two', 1, 2), 'resolve1(String, String, int, int)')

    def test_varargs(self):
        self.assertEqual(self.Overload.resolve1(1, 2, 3), 'resolve1(int...)')

    def test_two_args_and_varargs(self):
        self.assertEqual(self.Overload.resolve1('one', 'two', 1, 2, 3), 'resolve1(String, String, int...)')

    # Static context should make no difference to overload resolution.
    def test_mixed_static_and_instance(self):
        with self.assertRaisesRegexp(AttributeError, "static context"):
            self.Overload.resolve2("two")
        self.assertEqual(self.Overload().resolve2("two"), 'resolve2(String)')



    # FIXME test:
    # Java doesn't allow overloads (as opposed to overrides) added in derived classes to be
    # called (or even visible) through a base class interface. If the user wants to reproduce
    # this behaviour, they'll have to use the cast() function, otherwise the object's actual
    # class will always be used.
    #
