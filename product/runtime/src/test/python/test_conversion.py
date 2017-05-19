from __future__ import absolute_import, division, print_function
import unittest
from chaquopy import autoclass


class TestConversion(unittest.TestCase):

    def test_boolean(self):
        basics = autoclass('com.chaquo.python.Basics')()
        basics.fieldZ = False
        basics.fieldZ = True
        with self.assertRaisesRegexp(TypeError, "Cannot convert"):
            basics.fieldZ = 1

    def test_int(self):
        basics = autoclass('com.chaquo.python.Basics')()
        self.range_check_int(basics, "fieldB", 8)
        self.range_check_int(basics, "fieldS", 16)
        self.range_check_int(basics, "fieldI", 32)
        self.range_check_int(basics, "fieldJ", 64)

    def range_check_int(self, basics, field_name, bits):
        max_val = (2 ** (bits-1)) - 1
        min_val = -max_val - 1

        setattr(basics, field_name, min_val)
        setattr(basics, field_name, max_val)
        with self.assertRaisesRegexp(TypeError, "Cannot convert"):
            setattr(basics, field_name, True)
        with self.assertRaisesRegexp(TypeError, "Cannot convert"):
            setattr(basics, field_name, 1.23)
        with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
            setattr(basics, field_name, min_val - 1)
        with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
            setattr(basics, field_name, max_val + 1)

    def test_float(self):
        basics = autoclass('com.chaquo.python.Basics')()
        self.range_check_float(basics, "fieldF", 8)
        self.range_check_float(basics, "fieldD", 11)

    def range_check_float(self, basics, field_name, exponent_bits):
        max_exponent = (2 ** (exponent_bits - 1)) - 1

        setattr(basics, field_name, -(2.0 ** max_exponent))
        setattr(basics, field_name, 2.0 ** max_exponent)
        setattr(basics, field_name, float("nan"))
        setattr(basics, field_name, float("inf"))
        setattr(basics, field_name, float("-inf"))

        setattr(basics, field_name, 123)
        self.assertEqual(123, getattr(basics, field_name))
        with self.assertRaisesRegexp(TypeError, "Cannot convert"):
            setattr(basics, field_name, True)

        # In the case of double, the error will come from the unit test itself.
        with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
            setattr(basics, field_name, -(2.0 ** (max_exponent + 1)))
        with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
            setattr(basics, field_name, 2.0 ** (max_exponent + 1))

    def test_char(self):
        basics = autoclass('com.chaquo.python.Basics')()
        basics.fieldC = u"\u0000"
        basics.fieldC = u"\uFFFF"
        with self.assertRaisesRegexp(TypeError, "Cannot convert"):
            basics.fieldC = True
        with self.assertRaisesRegexp(TypeError, "Cannot convert"):
            basics.fieldC = 1
        with self.assertRaisesRegexp(TypeError, "expected a character"):
            basics.fieldC = "ab"
        with self.assertRaisesRegexp(TypeError, "non-BMP"):
            basics.fieldC = u"\U00010000"

    def test_class(self):
        Object = autoclass("java.lang.Object")
        String = autoclass("java.lang.String")
        Class = autoclass("java.lang.Class")

        self.assertTrue(Class.forName("java.lang.Object").isAssignableFrom(String))
        self.assertFalse(Class.forName("java.lang.String").isAssignableFrom(Object))
