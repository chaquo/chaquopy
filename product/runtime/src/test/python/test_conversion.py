from __future__ import absolute_import, division, print_function

from contextlib import contextmanager
import math
import six
import unittest

from chaquopy import autoclass


FLOAT32_EXPONENT_BITS = 8
FLOAT64_EXPONENT_BITS = 11


class TestConversion(unittest.TestCase):

    def setUp(self):
        self.obj = autoclass('com.chaquo.python.TestBasics')()
        self.conv_error = self.assertRaisesRegexp(TypeError, "Cannot convert")

    def test_null(self):
        self.verify_value(self.obj, "Z", None, context=self.conv_error, test_array=False)
        self.verify_value(self.obj, "Boolean", None)
        self.verify_value(self.obj, "String", None)
        # Assigning None to arrays is tested by verify_array.

    def test_unrelated(self):
        String = autoclass("java.lang.String")
        for value in ["hello", String, String("hello")]:
            self.verify_value(self.obj, "Boolean", value, context=self.conv_error)

    def test_parent_to_child(self):
        Object = autoclass("java.lang.Object")
        for name in ["Boolean", "ZArray"]:
            self.verify_value(self.obj, name, Object(), context=self.conv_error)

    def test_boolean(self):
        self.verify_boolean(self.obj, "Z")
        self.verify_boolean(self.obj, "Boolean")
        self.verify_boolean(self.obj, "Object", allow_int=True)

    def verify_boolean(self, obj, name, allow_int=False):
        self.verify_value(obj, name, False)
        self.verify_value(obj, name, True)
        self.verify_value(obj, name, 1,
                          context=self.arrOptional(TypeError, "Cannot convert", allow_int))
        self.verify_array(obj, name, False, True)

    def test_int(self):
        self.verify_int(self.obj, "B", 8)
        self.verify_int(self.obj, "S", 16)
        self.verify_int(self.obj, "I", 32)
        self.verify_int(self.obj, "J", 64)

        self.verify_int(self.obj, "Byte", 8)
        self.verify_int(self.obj, "Short", 16)
        self.verify_int(self.obj, "Integer", 32)
        self.verify_int(self.obj, "Long", 64)

        self.verify_int(self.obj, "Object", 64, allow_bool=True, allow_float=True)
        self.verify_int(self.obj, "Number", 64, allow_float=True)

    def verify_int(self, obj, name, bits, allow_bool=False, allow_float=False):
        max_val = (2 ** (bits-1)) - 1
        min_val = -max_val - 1

        self.verify_value(obj, name, min_val)
        self.verify_value(obj, name, max_val)
        self.verify_value(obj, name, True,
                          context=self.arrOptional(TypeError, "Cannot convert", allow_bool))
        self.verify_value(obj, name, 1.23,
                          context=self.arrOptional(TypeError, "Cannot convert", allow_float))
        self.verify_value(obj, name, min_val - 1,
                          context=self.assertRaisesRegexp(OverflowError, "too (big|large)"))
        self.verify_value(obj, name, max_val + 1,
                          context=self.assertRaisesRegexp(OverflowError, "too (big|large)"))
        self.verify_array(obj, name, min_val, max_val)

    def test_float(self):
        self.verify_float(self.obj, "F", FLOAT32_EXPONENT_BITS)
        self.verify_float(self.obj, "D", FLOAT64_EXPONENT_BITS)

        self.verify_float(self.obj, "Float", FLOAT32_EXPONENT_BITS)
        self.verify_float(self.obj, "Double", FLOAT64_EXPONENT_BITS)

        self.verify_float(self.obj, "Object", FLOAT64_EXPONENT_BITS, allow_bool=True)
        self.verify_float(self.obj, "Number", FLOAT64_EXPONENT_BITS)

    def verify_float(self, obj, name, exponent_bits, allow_bool=False):
        max_exponent = (2 ** (exponent_bits - 1)) - 1
        max_val = 2.0 ** max_exponent
        min_val = -max_val

        self.verify_value(obj, name, min_val)
        self.verify_value(obj, name, max_val)
        self.verify_value(obj, name, float("nan"),
                          verify=lambda expected, actual: self.assertTrue(math.isnan(actual)),
                          test_array=False)
        self.verify_value(obj, name, float("inf"))
        self.verify_value(obj, name, float("-inf"))

        # Floating-point types always accept an int.
        self.verify_value(obj, name, 123)

        self.verify_value(obj, name, True,
                          context=self.arrOptional(TypeError, "Cannot convert", allow_bool))

        if exponent_bits < FLOAT64_EXPONENT_BITS:
            self.verify_value(obj, name, -(2.0 ** (max_exponent + 1)),
                              context=self.assertRaisesRegexp(OverflowError, "too (big|large)"))
            self.verify_value(obj, name, 2.0 ** (max_exponent + 1),
                              context=self.assertRaisesRegexp(OverflowError, "too (big|large)"))

        # FIXME should be able to wrap in jfloat with truncate=True to avoid range checks.

        self.verify_array(obj, name, min_val, max_val)

    def test_char(self):
        self.verify_char(self.obj, "C")
        self.verify_char(self.obj, "Character")
        self.verify_char(self.obj, "Object", allow_bool=True, allow_int=True, allow_string=True)

    def verify_char(self, obj, name, allow_bool=False, allow_int=False, allow_string=False):
        min_val = u"\u0000"
        max_val = u"\uFFFF"
        self.verify_value(obj, name, min_val)
        self.verify_value(obj, name, max_val)

        self.verify_value(obj, name, "x")  # Will be a byte string in Python 2.

        self.verify_value(obj, name, True,
                          context=self.arrOptional(TypeError, "Cannot convert", allow_bool))
        self.verify_value(obj, name, 1,
                          context=self.arrOptional(TypeError, "Cannot convert", allow_int))
        self.verify_value(obj, name, "ab",
                          context=self.arrOptional(TypeError, "expected a character", allow_string))
        self.verify_value(obj, name, u"\U00010000",
                          context=self.arrOptional(TypeError, "non-BMP", allow_string))

        self.verify_array(obj, name, min_val, max_val)

    def test_string(self):
        for name in ["String", "CharSequence", "Object"]:
            self.verify_string(self.obj, name)
        for name in ["CArray", "CharacterArray"]:
            def verify(expected, actual):
                return actual == list(six.text_type(expected))
            self.verify_string(self.obj, name, verify=verify)

    def verify_string(self, obj, name, verify=None):
        self.verify_value(obj, name, "", verify=verify)        # Will be a byte string in Python 2.
        self.verify_value(obj, name, "hello", verify=verify)   #
        self.verify_value(obj, name, u"", verify=verify)
        self.verify_value(obj, name, u"hello", verify=verify)

        if not name.endswith("Array"):
            self.verify_array(obj, name, "hello", "world")
            self.verify_array(obj, name, u"hello", "world")
            self.verify_array(obj, name, u"hello", u"world")

    def test_class(self):
        for name in ["Klass", "Object"]:
            self.verify_class(self.obj, name)

    def verify_class(self, obj, name):
        System = autoclass("java.lang.System")
        Class = autoclass("java.lang.Class")
        self.verify_value(obj, name, System)
        self.verify_value(obj, name, Class)
        self.verify_array(obj, name, System, Class)

    def test_mixed_array(self):
        mixed =  [False, "hello"]
        self.verify_array(self.obj, "Object", *mixed)
        for name in ["ZArray", "BooleanArray", "StringArray"]:
            self.verify_value(self.obj, name, mixed, context=self.conv_error)

    def test_array_with_nulls(self):
        self.verify_array(self.obj, "String", "hello", None)
        self.verify_array(self.obj, "String", None, None)
        self.verify_value(self.obj, "ZArray", [None], context=self.conv_error)
        self.verify_value(self.obj, "ZArray", [None, False], context=self.conv_error)
        self.verify_value(self.obj, "ZArray", [False, None], context=self.conv_error)

    def verify_array(self, obj, name, val1, val2):
        for field in [name + "Array", "Object"]:  # All arrays are assignable to Object.
            self.verify_value(obj, field, None)
            self.verify_value(obj, field, [])
            # Single-element arrays are tested by verify_value.
            self.verify_value(obj, field, [val1, val2])
            self.verify_value(obj, field, [val2, val1])

    def verify_value(self, obj, name, value, context=None, verify=None, test_array=True):
        if context is None:
            context = no_context()
        if verify is None:
            verify = self.assertEqual
        self.verify_value_1(obj, name, value, context, verify)
        self.verify_value_1(type(obj), "Static" + name, value, context, verify)
        # Static members can also be accessed on an instance.
        self.verify_value_1(obj, "Static" + name, value, context, verify)

        if test_array and not name.endswith("Array"):
            self.verify_value(obj, name + "Array", [value], context, verify)

    def verify_value_1(self, obj, name, value, context, verify):
        field = "field" + name
        getter = "get" + name
        setter = "set" + name
        old_value = getattr(obj, field)

        with context:
            setattr(obj, field, value)
            verify(value, getattr(obj, field))
            verify(value, getattr(obj, getter)())  # Check new value is visible in Java as well.
        with context:
            getattr(obj, setter)(value)
            verify(value, getattr(obj, field))
            verify(value, getattr(obj, getter)())

        # Prevent consecutive static/instance tests leaking values to each other.
        setattr(obj, field, old_value)

    def arrOptional(self, cls, regexp, should_succeed):
        if should_succeed:
            return no_context()
        else:
            return self.assertRaisesRegexp(cls, regexp)


class no_context():
    def __enter__(self):
        pass
    def __exit__(self, *exc_info):
        pass
