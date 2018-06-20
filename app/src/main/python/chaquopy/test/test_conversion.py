from __future__ import absolute_import, division, print_function

from math import isnan
from java import jarray, jboolean, jbyte, jchar, jclass, jdouble, jfloat, jint, jlong, jshort
import sys

from .test_utils import FilterWarningsCase


FLOAT32_EXPONENT_BITS = 8
FLOAT64_EXPONENT_BITS = 11


class TestConversion(FilterWarningsCase):

    def setUp(self):
        super(TestConversion, self).setUp()
        self.obj = jclass('com.chaquo.python.TestBasics')()
        self.conv_error = self.assertRaisesRegexp(TypeError, "Cannot convert")
        self.too_big = self.assertRaisesRegexp(OverflowError, "too (big|large)")

    def conv_error_unless(self, flag):
        return None if flag else self.conv_error

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
        self.verify_boolean(self.obj, "Boolean", allow_null=True)
        self.verify_boolean(self.obj, "Object", allow_int=True, allow_null=True)

    def verify_boolean(self, obj, name, allow_int=False, allow_null=False):
        self.verify_value(obj, name, True, wrapper=jboolean)

        # Wrapper type and bounds checks are tested in test_signatures.
        self.verify_value(obj, name, 1, context=self.conv_error_unless(allow_int))
        self.verify_value(obj, name, None, context=self.conv_error_unless(allow_null))

        self.verify_array(obj, name, False, True)

    def test_int(self):
        self.verify_int(self.obj, "B", 8, jbyte)
        self.verify_int(self.obj, "S", 16, jshort)
        self.verify_int(self.obj, "I", 32, jint)
        self.verify_int(self.obj, "J", 64, jlong)

        self.verify_int(self.obj, "Byte", 8, jbyte, allow_null=True)
        self.verify_int(self.obj, "Short", 16, jshort, allow_null=True)
        self.verify_int(self.obj, "Integer", 32, jint, allow_null=True)
        self.verify_int(self.obj, "Long", 64, jlong, allow_null=True)

        # Bounds will only be checked if we use the wrappers, so we can't test wrapped and
        # unwrapped together.
        self.verify_int(self.obj, "Object", 64, allow_bool=True, allow_float=True, allow_null=True)
        self.verify_int(self.obj, "Number", 64, allow_float=True, allow_null=True)
        for wrapper in [jbyte, jshort, jint, jlong]:
            self.verify_value(self.obj, "Object", 123, wrapper=wrapper)
            self.verify_value(self.obj, "Number", 123, wrapper=wrapper)

    def verify_int(self, obj, name, bits, wrapper=None, allow_bool=False, allow_float=False,
                   allow_null=False):
        max_val = (2 ** (bits - 1)) - 1
        min_val = -max_val - 1

        self.verify_value(obj, name, min_val, wrapper=wrapper)
        self.verify_value(obj, name, max_val, wrapper=wrapper)
        if sys.version_info[0] < 3:
            self.verify_value(obj, name, long(123), wrapper=wrapper)  # noqa: F821

        # Wrapper type and bounds checks are tested in test_signatures.
        self.verify_value(obj, name, True, context=self.conv_error_unless(allow_bool))
        self.verify_value(obj, name, 1.23, context=self.conv_error_unless(allow_float))
        self.verify_value(obj, name, None, context=self.conv_error_unless(allow_null))

        self.verify_value(obj, name, min_val - 1, context=self.too_big)
        self.verify_value(obj, name, max_val + 1, context=self.too_big)
        self.verify_array(obj, name, min_val, max_val)

    def test_float(self):
        self.verify_float(self.obj, "F", FLOAT32_EXPONENT_BITS, jfloat)
        self.verify_float(self.obj, "D", FLOAT64_EXPONENT_BITS, jdouble)

        self.verify_float(self.obj, "Float", FLOAT32_EXPONENT_BITS, jfloat, allow_null=True)
        self.verify_float(self.obj, "Double", FLOAT64_EXPONENT_BITS, jdouble, allow_null=True)

        # Bounds will only be checked if we use the wrappers, so we can't test wrapped and
        # unwrapped together.
        self.verify_float(self.obj, "Object", FLOAT64_EXPONENT_BITS, allow_bool=True,
                          allow_null=True)
        self.verify_float(self.obj, "Number", FLOAT64_EXPONENT_BITS, allow_null=True)
        for wrapper in [jfloat, jdouble]:
            self.verify_value(self.obj, "Object", 123, wrapper=wrapper)
            self.verify_value(self.obj, "Number", 123, wrapper=wrapper)

    def verify_float(self, obj, name, exponent_bits, wrapper=None, allow_bool=False,
                     allow_null=False):
        max_exponent = (2 ** (exponent_bits - 1)) - 1
        max_val = 2.0 ** max_exponent
        min_val = -max_val

        for val in [123,  # Floating-point types always accept an int.
                    min_val, max_val, float("inf"), float("-inf")]:
            self.verify_value(obj, name, val, wrapper=wrapper)
        if sys.version_info[0] < 3:
            self.verify_value(obj, name, long(123), wrapper=wrapper)  # noqa: F821

        self.verify_value(obj, name, float("nan"),  # NaN is unequal to everything including itself.
                          wrapper=wrapper,
                          verify=lambda expected, actual: self.assertTrue(isnan(actual)))

        # Wrapper type and bounds checks are tested in test_signatures.
        self.verify_value(obj, name, True, context=self.conv_error_unless(allow_bool))
        self.verify_value(obj, name, None, context=self.conv_error_unless(allow_null))

        if exponent_bits < FLOAT64_EXPONENT_BITS:
            for val in [2.0 ** (max_exponent + 1),
                        -2.0 ** (max_exponent + 1)]:
                self.verify_value(obj, name, val, context=self.too_big)

        self.verify_array(obj, name, min_val, max_val)

    def test_char(self):
        self.verify_char(self.obj, "C")
        self.verify_char(self.obj, "Character", allow_null=True)
        self.verify_char(self.obj, "Object", allow_bool=True, allow_int=True, allow_null=True,
                         allow_string=True)

    def verify_char(self, obj, name, allow_bool=False, allow_int=False, allow_null=False,
                    allow_string=False):
        min_val = u"\u0000"
        max_val = u"\uFFFF"
        self.verify_value(obj, name, min_val, wrapper=jchar)
        self.verify_value(obj, name, max_val, wrapper=jchar)

        self.verify_value(obj, name, "x", wrapper=jchar)  # Will be a byte string in Python 2.

        # Wrapper type and bounds checks are tested in test_signatures.
        self.verify_value(obj, name, True, context=self.conv_error_unless(allow_bool))
        self.verify_value(obj, name, 1, context=self.conv_error_unless(allow_int))
        self.verify_value(obj, name, None, context=self.conv_error_unless(allow_null))
        self.verify_value(obj, name, "ab",
                          context=(None if allow_string else
                                   self.assertRaisesRegexp((TypeError, ValueError),
                                                           r"(expected a character|"
                                                           r"only single character).*length 2")))
        self.verify_value(obj, name, u"\U00010000",
                          context=(None if allow_string else
                                   self.assertRaisesRegexp(TypeError, "non-BMP")))

        self.verify_array(obj, name, min_val, max_val)

    def test_string(self):
        for name in ["String", "CharSequence", "Object"]:
            self.verify_string(self.obj, name)

        # No implicit conversions should happen between strings and character arrays.
        for name in ["CArray", "CharacterArray"]:
            self.verify_value(self.obj, name, "hello", context=self.conv_error)

        # Or between between integers and characters (unlike in Java).
        for name, value in [("I", "x"), ("C", 42)]:
            self.verify_value(self.obj, name, value, context=self.conv_error)

    def verify_string(self, obj, name):
        for val in [u"", u"h", u"hello",
                    u"\u0000",          # Null character       # (handled differently by
                    u"\U00012345"]:     # Non-BMP character    #   "modified UTF-8")
            self.verify_value(obj, name, val)

        # Byte strings can be implicitly converted to Java Strings only on Python 2. However,
        # if the target type is Object, Python 3 will fall back on the default conversion of a
        # Python iterable to Object[].
        context = verify = None
        if name == "Object":
            def verify(expected, actual):
                self.assertEqual(expected, actual)
                self.assertIsInstance(actual, (unicode if sys.version_info[0] < 3  # noqa: F821
                                               else jarray("Ljava/lang/Object;")))
        elif sys.version_info[0] >= 3:
            context = self.conv_error
        for val in [b"", b"h", b"hello"]:
            self.verify_value(obj, name, val, context=context, verify=verify)

        # Even on Python 2, only ASCII byte strings can be converted.
        if sys.version_info[0] < 3:
            self.verify_value(obj, name, b"\x99",
                              context=self.assertRaisesRegexp(UnicodeDecodeError, "'ascii' codec"))

    def test_class(self):
        for name in ["Klass", "Object"]:
            self.verify_class(self.obj, name)

    def verify_class(self, obj, name):
        System = jclass("java.lang.System")
        Class = jclass("java.lang.Class")
        self.verify_value(obj, name, System)
        self.verify_value(obj, name, Class)
        self.verify_array(obj, name, System, Class)

    # There are more array conversion tests in test_array.py.
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
        for a in [[None], [None, False], [False, None]]:
            self.verify_value(self.obj, "ZArray", a, context=self.conv_error)

    def verify_array(self, obj, name, val1, val2):
        self.assertNotEqual(val1, val2)

        nameArray = name + "Array"
        for a in [None, [], [val1], [val2], [val1, val2]]:
            self.verify_value(obj, nameArray, a)

        # Test modification of array obtained from a field, and from a method.
        field = "field" + nameArray
        getter = getattr(obj, "get" + nameArray)

        def verify_array_modify(array_source):
            setattr(obj, field, [val1, val2])
            array = array_source()
            self.assertEqual([val1, val2], array)
            array[0] = val2
            array[1] = val1
            self.assertEqual([val2, val1], getter())

        verify_array_modify(lambda: getattr(obj, field))
        verify_array_modify(getter)

    def verify_value(self, obj, name, value, context=None, verify=None, wrapper=None):
        if context is None:
            context = no_context()
        if verify is None:
            verify = self.assertEqual

        self.verify_value_1(obj, name, value, value, context, verify)
        if wrapper:
            self.verify_value_1(obj, name, wrapper(value), value, context, verify)

    def verify_value_1(self, obj, name, input, output, context, verify):
        self.verify_value_2(obj, name, input, output, context, verify)
        self.verify_value_2(type(obj), "Static" + name, input, output, context, verify)
        # Static members can also be accessed on an instance.
        self.verify_value_2(obj, "Static" + name, input, output, context, verify)

    def verify_value_2(self, obj, name, input, output, context, verify):
        field = "field" + name

        # If the original and test values are the same then the test is pointless.
        original = getattr(obj, field)
        with self.assertRaises(Exception, msg="{} is already {}".format(field, original)):
            verify(output, original)

        with context:
            setattr(obj, field, input)
            verify(output, getattr(obj, "get" + name)())
        setattr(obj, field, original)

        with context:
            getattr(obj, "set" + name)(input)
            verify(output, getattr(obj, field))
        setattr(obj, field, original)


class no_context():
    def __enter__(self):
        pass
    def __exit__(self, *exc_info):
        pass
