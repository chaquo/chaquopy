from __future__ import absolute_import, division, print_function

import math
import unittest

from chaquopy import *
from chaquopy.signatures import *


class TestSignatures(unittest.TestCase):

    def test_jni_sig(self):
        Object = autoclass("java.lang.Object")

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

    def test_jni_method_sig(self):
        Object = autoclass("java.lang.Object")
        String = autoclass("java.lang.String")
        Integer = autoclass("java.lang.Integer")

        self.assertEquals("()V", jni_method_sig(jvoid, []))
        self.assertEquals("()J", jni_method_sig(jlong, []))
        self.assertEquals("()Ljava/lang/String;", jni_method_sig(String, []))

        self.assertEquals("(Ljava/lang/Integer;)Ljava/lang/String;",
                          jni_method_sig(String, [Integer]))
        self.assertEquals("(Ljava/lang/Object;ZLjava/lang/Integer;)D",
                          jni_method_sig(jdouble, [Object, jboolean, Integer]))

        self.assertEquals("()[I", jni_method_sig(jarray(jint), []))
        self.assertEquals("([I[Z)V", jni_method_sig(jvoid, [jarray(jint), jarray(jboolean)]))

    def test_jvoid(self):
        with self.assertRaisesRegexp(TypeError, "Cannot create"):
            jvoid()

    # We don't test .value with any of the wrappers, because that's a non-public implementation
    # detail.
    #
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
        max_val = (2 ** (bits-1)) - 1
        min_val = -max_val - 1

        for val in [min_val, max_val]:
            self.assertEquals("{}({})".format(cls.__name__, val),
                              str(cls(val)))

        for val in [min_val - 1, max_val + 1]:
            with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
                cls(val)
            self.assertEquals("{}({})".format(cls.__name__, truncate(val, bits)),
                              str(cls(val, truncate=True)))

        with self.assertRaisesRegexp(TypeError, "integer"):
            cls("42")
        with self.assertRaisesRegexp(TypeError, "integer"):
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

        with self.assertRaisesRegexp(TypeError, "float"):
            cls("42")
        with self.assertRaisesRegexp(TypeError, "float"):
            cls(True)

    def test_char(self):
        self.assertEquals("jchar('x')", str(jchar("x")))
        self.assertEquals("jchar('x')", str(jchar(u"x")))

        with self.assertRaisesRegexp(TypeError, "expected a character"):
            jchar("ab")
        with self.assertRaisesRegexp(TypeError, "non-BMP"):
            jchar(u"\U00010000")

    def test_array(self):
        list_bool = [True, False]
        for jarray_Z in [jarray(jboolean, list_bool), jarray(jboolean)(list_bool),
                         jarray("Z", list_bool)]:
            self.assertEqual("jarray_Z", type(jarray_Z).__name__)
            self.assertEqual("jarray('Z', {!r})".format(list_bool), str(jarray_Z))

        list_list_bool = [[True, False], [False, True]]
        jarray_jarray_Z = jarray(jarray(jboolean), list_list_bool)
        self.assertEqual("jarray_[Z", type(jarray_jarray_Z).__name__)
        self.assertEqual("jarray('[Z', {!r})".format(list_list_bool), str(jarray_jarray_Z))

        list_str = ["one", "two"]
        String = autoclass("java.lang.String")
        jarray_String = jarray(String, list_str)
        self.assertEqual("jarray_Ljava/lang/String;", type(jarray_String).__name__)
        self.assertEqual("jarray('Ljava/lang/String;', {!r})".format(list_str), str(jarray_String))


def truncate(value, bits):
    value &= (2 ** bits) - 1    # Remove high bits and map negative numbers to high positive ones
    value ^= 2 ** (bits - 1)    # Swap negatives and positives
    value -= 2 ** (bits - 1)    # Move everything back down to its proper place
    return value
