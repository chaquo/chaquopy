# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from java import jarray, jboolean, jbyte, jchar, jclass, jdouble, jfloat, jint, jlong, jshort, jvoid
from java.chaquopy import jni_sig
import math
import sys

from .test_utils import FilterWarningsCase


class TestSignatures(FilterWarningsCase):

    # jni_sig is not part of the public API and should not be accessed by user code.
    def test_jni_sig(self):
        Object = jclass("java.lang.Object")

        self.assertEquals("V", jni_sig(jvoid))
        self.assertEquals("Z", jni_sig(jboolean))
        self.assertEquals("B", jni_sig(jbyte))
        self.assertEquals("C", jni_sig(jchar))
        self.assertEquals("D", jni_sig(jdouble))
        self.assertEquals("F", jni_sig(jfloat))
        self.assertEquals("I", jni_sig(jint))
        self.assertEquals("J", jni_sig(jlong))
        self.assertEquals("S", jni_sig(jshort))
        self.assertEquals("Ljava/lang/Object;", jni_sig(Object))

        self.assertEquals("[Z", jni_sig(jarray(jboolean)))
        self.assertEquals("[[Z", jni_sig(jarray(jarray(jboolean))))

        self.assertEquals("[Ljava/lang/Object;", jni_sig(jarray(Object)))
        self.assertEquals("[[Ljava/lang/Object;", jni_sig(jarray(jarray(Object))))

    def test_jvoid(self):
        with self.assertRaisesRegexp(TypeError, "Cannot create"):
            jvoid()

    # Tests for passing the wrappers to fields and methods are in test_conversion.
    def test_boolean(self):
        self.assertEquals("jboolean(True)", str(jboolean(True)))
        self.assertEquals("jboolean(True)", str(jboolean(42)))
        self.assertEquals("jboolean(True)", str(jboolean("hello")))
        self.assertEquals("jboolean(False)", str(jboolean("")))
        self.assertEquals("jboolean(False)", str(jboolean([])))

    def test_int(self):
        self.verify_int(jbyte, 8)
        self.verify_int(jshort, 16)
        self.verify_int(jint, 32)
        self.verify_int(jlong, 64)

    def verify_int(self, cls, bits):
        max_val = (2 ** (bits - 1)) - 1
        min_val = -max_val - 1

        for val in [min_val, max_val]:
            self.assertEquals("{}({})".format(cls.__name__, val),
                              str(cls(val)))

        for val in [min_val - 1, max_val + 1]:
            with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
                cls(val)
            self.assertEquals("{}({})".format(cls.__name__, truncate(val, bits)),
                              str(cls(val, truncate=True)))

        with self.assertRaisesRegexp(TypeError, "an integer is required"):
            cls("42")
        with self.assertRaisesRegexp(TypeError, "an integer is required"):
            cls(42.0)
        with self.assertRaisesRegexp(TypeError, "an integer is required"):
            cls(True)

    def test_float(self):
        self.verify_float(jfloat, 8)
        self.verify_float(jdouble, 11)

    def verify_float(self, cls, exponent_bits):
        max_exponent = (2 ** (exponent_bits - 1)) - 1
        max_val = 2.0 ** max_exponent
        min_val = -max_val

        for val in [42, 42.0, min_val, max_val, float("inf"), float("-inf"), float("nan")]:
            self.assertEquals("{}({})".format(cls.__name__, float(val)), str(cls(val)))

        if exponent_bits < 11:
            for val in [2.0 ** (max_exponent + 1),
                        -2.0 ** (max_exponent + 1)]:
                with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
                    cls(val)
                self.assertEquals("{}({})".format(cls.__name__,
                                                  math.copysign(1, val) * float("inf")),
                                  str(cls(val, truncate=True)))

        with self.assertRaisesRegexp(TypeError, "a float or integer is required"):
            cls("42")
        with self.assertRaisesRegexp(TypeError, "a float or integer is required"):
            cls(True)

    def test_char(self):
        self.assertEquals("jchar('x')", str(jchar("x")))
        self.assertEquals("jchar('x')", str(jchar(u"x")))

        zhong_j = jchar(u"中")
        zhong_j_u = u"jchar('中')"
        if sys.version_info[0] < 3:
            self.assertEqual(zhong_j_u.encode("utf-8"), str(zhong_j))
        else:
            self.assertEqual(zhong_j_u, str(zhong_j))

        with self.assertRaisesRegexp((TypeError, ValueError),
                                     r"(expected a character|only single character).*length 2"):
            jchar("ab")
        with self.assertRaisesRegexp(TypeError, "non-BMP"):
            jchar(u"\U00010000")

    def test_array(self):
        list_bool = [True, False]
        for jarray_Z in [jarray(jboolean)(list_bool), jarray("Z")(list_bool)]:
            self.assertEqual("[Z", type(jarray_Z).__name__)
            self.assertEqual("jarray('Z')({!r})".format(list_bool), str(jarray_Z))

        list_list_bool = [[True, False], [False, True]]
        jarray_jarray_Z = jarray(jarray(jboolean))(list_list_bool)
        self.assertEqual("[[Z", type(jarray_jarray_Z).__name__)
        self.assertEqual("jarray('[Z')({!r})".format(list_list_bool), str(jarray_jarray_Z))

        list_str = ["one", "two"]
        String = jclass("java.lang.String")
        jarray_String = jarray(String)(list_str)
        self.assertEqual("[Ljava/lang/String;", type(jarray_String).__name__)
        self.assertEqual("jarray('Ljava/lang/String;')({!r})".format(list_str), str(jarray_String))


def truncate(value, bits):
    value &= (2 ** bits) - 1    # Remove high bits and map negative numbers to high positive ones
    value ^= 2 ** (bits - 1)    # Swap negatives and positives
    value -= 2 ** (bits - 1)    # Move everything back down to its proper place
    return value
