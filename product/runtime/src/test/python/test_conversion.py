from __future__ import absolute_import, division, print_function

from contextlib import contextmanager
import math
import unittest

from chaquopy import autoclass


class TestConversion(unittest.TestCase):

    def test_boolean(self):
        obj = autoclass('com.chaquo.python.TestConversion')()
        self.check_boolean_field(obj, "fieldZ")
        self.check_boolean_field(obj, "fieldBoolean")
        self.check_boolean_field(obj, "fieldObject", allow_int=True)

    def check_boolean_field(self, obj, field, allow_int=False):
        self.verify_value(obj, field, False)
        self.verify_value(obj, field, True)
        with self.assertRaisesRegexpOptional(TypeError, "Cannot convert", allow_int):
            self.verify_value(obj, field, 1)

    def test_int(self):
        obj = autoclass('com.chaquo.python.TestConversion')()
        self.check_int_field(obj, "fieldB", 8)
        self.check_int_field(obj, "fieldS", 16)
        self.check_int_field(obj, "fieldI", 32)
        self.check_int_field(obj, "fieldJ", 64)

        self.check_int_field(obj, "fieldByte", 8)
        self.check_int_field(obj, "fieldShort", 16)
        self.check_int_field(obj, "fieldInteger", 32)
        self.check_int_field(obj, "fieldLong", 64)

        self.check_int_field(obj, "fieldObject", 64, allow_bool=True, allow_float=True)
        self.check_int_field(obj, "fieldNumber", 64, allow_float=True)

    def check_int_field(self, obj, field, bits, allow_bool=False, allow_float=False):
        max_val = (2 ** (bits-1)) - 1
        min_val = -max_val - 1

        self.verify_value(obj, field, min_val)
        self.verify_value(obj, field, max_val)
        with self.assertRaisesRegexpOptional(TypeError, "Cannot convert", allow_bool):
            self.verify_value(obj, field, True)
        with self.assertRaisesRegexpOptional(TypeError, "Cannot convert", allow_float):
            self.verify_value(obj, field, 1.23)
        with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
            self.verify_value(obj, field, min_val - 1)
        with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
            self.verify_value(obj, field, max_val + 1)

    def test_float(self):
        obj = autoclass('com.chaquo.python.TestConversion')()
        self.check_float_field(obj, "fieldF", 8)
        self.check_float_field(obj, "fieldD", 11)

        self.check_float_field(obj, "fieldFloat", 8)
        self.check_float_field(obj, "fieldDouble", 11)

        self.check_float_field(obj, "fieldObject", 11, allow_bool=True)
        self.check_float_field(obj, "fieldNumber", 11)

    def check_float_field(self, obj, field, exponent_bits, allow_bool=False):
        max_exponent = (2 ** (exponent_bits - 1)) - 1

        self.verify_value(obj, field, -(2.0 ** max_exponent))
        self.verify_value(obj, field, 2.0 ** max_exponent)
        self.verify_value(obj, field, float("nan"),
                          verify=lambda expected, actual: self.assertTrue(math.isnan(actual)))
        self.verify_value(obj, field, float("inf"))
        self.verify_value(obj, field, float("-inf"))

        # Floating-point fields always accept an int.
        self.verify_value(obj, field, 123)

        with self.assertRaisesRegexpOptional(TypeError, "Cannot convert", allow_bool):
            self.verify_value(obj, field, True)

        # In the case of double, the error will come from the unit test itself.
        with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
            self.verify_value(obj, field, -(2.0 ** (max_exponent + 1)))
        with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
            self.verify_value(obj, field, 2.0 ** (max_exponent + 1))

        # FIXME should be able to wrap in jfloat with truncate=True to avoid range checks.

    def test_char(self):
        obj = autoclass('com.chaquo.python.TestConversion')()
        self.check_char_field(obj, "fieldC")
        self.check_char_field(obj, "fieldCharacter")
        self.check_char_field(obj, "fieldObject", allow_bool=True, allow_int=True, allow_string=True)

    def check_char_field(self, obj, field, allow_bool=False, allow_int=False, allow_string=False):
        self.verify_value(obj, field, "x")  # Will be a byte string in Python 2.
        self.verify_value(obj, field, u"\u0000")
        self.verify_value(obj, field, u"\uFFFF")

        with self.assertRaisesRegexpOptional(TypeError, "Cannot convert", allow_bool):
            self.verify_value(obj, field, True)
        with self.assertRaisesRegexpOptional(TypeError, "Cannot convert", allow_int):
            self.verify_value(obj, field, 1)
        with self.assertRaisesRegexpOptional(TypeError, "expected a character", allow_string):
            self.verify_value(obj, field, "ab")
        with self.assertRaisesRegexpOptional(TypeError, "non-BMP", allow_string):
            self.verify_value(obj, field, u"\U00010000")

    # FIXME extend this to generate, from a suffix, names of fields, static fields, methods
    # which take an argument and set a field, and methods which return a field. Rewrite Basics
    # to do this, remove TestConversion. Remove those parts of test_basics which duplicate
    # this, and move the rest, along with test_reflect, into test_class.

    def verify_value(self, obj, field, value, verify=None):
        if verify is None:
            verify = self.assertEqual
        setattr(obj, field, value)
        verify(value, getattr(obj, field))

    @contextmanager
    def assertRaisesRegexpOptional(self, cls, regexp, should_succeed):
        if should_succeed:
            yield
        else:
            with self.assertRaisesRegexp(cls, regexp):
                yield

    def test_class(self):
        Object = autoclass("java.lang.Object")
        String = autoclass("java.lang.String")
        Class = autoclass("java.lang.Class")

        self.assertTrue(Class.forName("java.lang.Object").isAssignableFrom(String))
        self.assertFalse(Class.forName("java.lang.String").isAssignableFrom(Object))
