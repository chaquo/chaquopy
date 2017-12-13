from __future__ import absolute_import, division, print_function

import math
import unittest

from java import jarray, jboolean, jbyte, jchar, jclass, jdouble, jfloat, jint, jlong, jshort


FLOAT32_EXPONENT_BITS = 8
FLOAT64_EXPONENT_BITS = 11


class TestConversion(unittest.TestCase):

    def setUp(self):
        self.obj = jclass('com.chaquo.python.TestBasics')()
        self.conv_error = self.assertRaisesRegexp(TypeError, "Cannot convert")

    def test_null(self):
        self.verify_value(self.obj, "Z", None, context=self.conv_error)
        self.verify_value(self.obj, "Boolean", None)
        self.verify_value(self.obj, "String", None)
        # Assigning None to arrays is tested by verify_array.

    def test_unrelated(self):
        String = jclass("java.lang.String")
        for value in ["hello", String, String("hello")]:
            self.verify_value(self.obj, "Boolean", value, context=self.conv_error)

    def test_parent_to_child(self):
        Object = jclass("java.lang.Object")
        for name in ["Boolean", "ZArray"]:
            self.verify_value(self.obj, name, Object(), context=self.conv_error)

    def test_boolean(self):
        self.verify_boolean(self.obj, "Z")
        self.verify_boolean(self.obj, "Boolean")
        self.verify_boolean(self.obj, "Object", allow_int=True)

    def verify_boolean(self, obj, name, allow_int=False):
        self.verify_value(obj, name, False, wrapper=jboolean)
        self.verify_value(obj, name, True, wrapper=jboolean)

        # Wrapper type and bounds checks are tested in test_signatures.
        self.verify_value(obj, name, 1,
                          context=self.arrOptional(TypeError, "Cannot convert", allow_int))

        self.verify_array(obj, name, False, True)

    def test_int(self):
        self.verify_int(self.obj, "B", 8, jbyte)
        self.verify_int(self.obj, "S", 16, jshort)
        self.verify_int(self.obj, "I", 32, jint)
        self.verify_int(self.obj, "J", 64, jlong)

        self.verify_int(self.obj, "Byte", 8, jbyte)
        self.verify_int(self.obj, "Short", 16, jshort)
        self.verify_int(self.obj, "Integer", 32, jint)
        self.verify_int(self.obj, "Long", 64, jlong)

        # Bounds will only be checked if we use the wrappers, so we can't test wrapped and
        # unwrapped together.
        self.verify_int(self.obj, "Object", 64, allow_bool=True, allow_float=True)
        self.verify_int(self.obj, "Number", 64, allow_float=True)
        for wrapper in [jbyte, jshort, jint, jlong]:
            self.verify_value(self.obj, "Object", 42)
            self.verify_value(self.obj, "Number", 42)

    def verify_int(self, obj, name, bits, wrapper=None, allow_bool=False, allow_float=False):
        max_val = (2 ** (bits - 1)) - 1
        min_val = -max_val - 1

        self.verify_value(obj, name, min_val, wrapper=wrapper)
        self.verify_value(obj, name, max_val, wrapper=wrapper)

        # Wrapper type and bounds checks are tested in test_signatures.
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
        self.verify_float(self.obj, "F", FLOAT32_EXPONENT_BITS, jfloat)
        self.verify_float(self.obj, "D", FLOAT64_EXPONENT_BITS, jdouble)

        self.verify_float(self.obj, "Float", FLOAT32_EXPONENT_BITS, jfloat)
        self.verify_float(self.obj, "Double", FLOAT64_EXPONENT_BITS, jdouble)

        # Bounds will only be checked if we use the wrappers, so we can't test wrapped and
        # unwrapped together.
        self.verify_float(self.obj, "Object", FLOAT64_EXPONENT_BITS, allow_bool=True)
        self.verify_float(self.obj, "Number", FLOAT64_EXPONENT_BITS)
        for wrapper in [jfloat, jdouble]:
            self.verify_value(self.obj, "Object", 42)
            self.verify_value(self.obj, "Number", 42)

    def verify_float(self, obj, name, exponent_bits, wrapper=None, allow_bool=False):
        max_exponent = (2 ** (exponent_bits - 1)) - 1
        max_val = 2.0 ** max_exponent
        min_val = -max_val

        for val in [42,  # Floating-point types always accept an int.
                    min_val, max_val, float("inf"), float("-inf")]:
            self.verify_value(obj, name, val, wrapper=wrapper)

        self.verify_value(obj, name, float("nan"),  # NaN is unequal to everything including itself.
                          wrapper=wrapper,
                          verify=lambda expected, actual: self.assertTrue(math.isnan(actual)))

        # Wrapper type and bounds checks are tested in test_signatures.
        self.verify_value(obj, name, True,
                          context=self.arrOptional(TypeError, "Cannot convert", allow_bool))

        if exponent_bits < FLOAT64_EXPONENT_BITS:
            for val in [2.0 ** (max_exponent + 1),
                        -2.0 ** (max_exponent + 1)]:
                self.verify_value(obj, name, val,
                                  context=self.assertRaisesRegexp(OverflowError, "too (big|large)"))

        self.verify_array(obj, name, min_val, max_val)

    def test_char(self):
        self.verify_char(self.obj, "C")
        self.verify_char(self.obj, "Character")
        self.verify_char(self.obj, "Object", allow_bool=True, allow_int=True, allow_string=True)

    def verify_char(self, obj, name, allow_bool=False, allow_int=False, allow_string=False):
        min_val = u"\u0000"
        max_val = u"\uFFFF"
        self.verify_value(obj, name, min_val, wrapper=jchar)
        self.verify_value(obj, name, max_val, wrapper=jchar)

        self.verify_value(obj, name, "x", wrapper=jchar)  # Will be a byte string in Python 2.

        # Wrapper type and bounds checks are tested in test_signatures.
        self.verify_value(obj, name, True,
                          context=self.arrOptional(TypeError, "Cannot convert", allow_bool))
        self.verify_value(obj, name, 1,
                          context=self.arrOptional(TypeError, "Cannot convert", allow_int))
        self.verify_value(obj, name, "ab",
                          context=self.arrOptional(
                              (TypeError, ValueError),
                              r"(expected a character|only single character).*length 2",
                              allow_string))
        self.verify_value(obj, name, u"\U00010000",
                          context=self.arrOptional(TypeError, "non-BMP", allow_string))

        self.verify_array(obj, name, min_val, max_val)

    def test_string(self):
        for name in ["String", "CharSequence", "Object"]:
            self.verify_string(self.obj, name)
        for name in ["CArray", "CharacterArray"]:
            self.verify_value(self.obj, name, "hello", context=self.conv_error)

    def verify_string(self, obj, name):
        for val in ["", "h", "hello",   # Will be byte strings in Python 2
                    u"\u0000",          # Null character       # (handled differently by
                    u"\U00012345"]:     # Non-BMP character    #   "modified UTF-8")
            self.verify_value(obj, name, val)

    def test_class(self):
        for name in ["Klass", "Object"]:
            self.verify_class(self.obj, name)

    def verify_class(self, obj, name):
        System = jclass("java.lang.System")
        Class = jclass("java.lang.Class")
        self.verify_value(obj, name, System)
        self.verify_value(obj, name, Class)
        self.verify_array(obj, name, System, Class)

    # More conversion tests in test_array.py
    def test_array(self):
        Object = jclass("java.lang.Object")
        Number = jclass("java.lang.Number")
        self.verify_value(self.obj, "ObjectArray", jarray(Number)([11, 22]))
        with self.conv_error:  # Can't use `context`: exception is raised by `jarray` constructor.
            self.verify_value(self.obj, "NumberArray", jarray(Object)([False, True]))

        # Arrays of primitives are not assignable to arrays of Object.
        self.verify_value(self.obj, "ObjectArray", jarray(jboolean)([False, True]),
                          context=self.conv_error)

    def test_mixed_array(self):
        mixed = [False, "hello"]
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
        field = name + "Array"
        self.verify_value(obj, field, None)
        self.verify_value(obj, field, [])
        # Single-element arrays are tested by verify_value.
        self.verify_value(obj, field, [val1, val2])
        self.verify_value(obj, field, [val2, val1])

        # Test modification of array obtained from a field, and from a method.
        fieldArray, getArray, setArray = [prefix + name + "Array"
                                          for prefix in ("field", "get", "set")]

        def verify_array_modify(array_source):
            setattr(obj, fieldArray, [val1, val2])
            array = array_source()
            self.assertEqual([val1, val2], array)
            array[0] = val2
            array[1] = val1
            self.assertEqual([val2, val1], getattr(obj, fieldArray))
            self.assertEqual([val2, val1], getattr(obj, getArray)())

        verify_array_modify(lambda: getattr(obj, fieldArray))
        verify_array_modify(lambda: getattr(obj, getArray)())

    def verify_value(self, obj, name, value, context=None, verify=None, wrapper=None):
        if context is None:
            context = no_context()
        if verify is None:
            verify = self.assertEqual

        self.verify_value_1(obj, name, value, context, verify)
        if wrapper:
            self.verify_value_1(obj, name, value, context, verify, wrapper)

    def verify_value_1(self, obj, name, value, context, verify, wrapper=(lambda value: value)):
        self.verify_value_2(obj, name, value, context, verify, wrapper)
        self.verify_value_2(type(obj), "Static" + name, value, context, verify, wrapper)
        # Static members can also be accessed on an instance.
        self.verify_value_2(obj, "Static" + name, value, context, verify, wrapper)

        if not name.endswith("Array"):
            self.verify_value_1(obj, name + "Array", value, context,
                                verify=lambda expected, actual: verify(expected, actual[0]),
                                wrapper=lambda value: [wrapper(value)])

    def verify_value_2(self, obj, name, value, context, verify, wrapper):
        field = "field" + name
        getter = "get" + name
        setter = "set" + name
        old_value = getattr(obj, field)

        with context:
            setattr(obj, field, wrapper(value))
            verify(value, getattr(obj, field))
            verify(value, getattr(obj, getter)())  # Check new value is visible in Java as well.
        with context:
            getattr(obj, setter)(wrapper(value))
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
