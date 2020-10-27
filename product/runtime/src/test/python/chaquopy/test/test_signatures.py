from java import jarray, jboolean, jbyte, jchar, jclass, jdouble, jfloat, jint, jlong, jshort, jvoid
from java.chaquopy import jni_sig
import math

from .test_utils import FilterWarningsCase


class TestSignatures(FilterWarningsCase):

    def setUp(self):
        super().setUp()
        self.too_big = self.assertRaisesRegex(OverflowError, "too (big|large) to convert")

    # jni_sig is not part of the public API and should not be accessed by user code.
    def test_jni_sig(self):
        Object = jclass("java.lang.Object")

        self.assertEqual("V", jni_sig(jvoid))
        self.assertEqual("Z", jni_sig(jboolean))
        self.assertEqual("B", jni_sig(jbyte))
        self.assertEqual("C", jni_sig(jchar))
        self.assertEqual("D", jni_sig(jdouble))
        self.assertEqual("F", jni_sig(jfloat))
        self.assertEqual("I", jni_sig(jint))
        self.assertEqual("J", jni_sig(jlong))
        self.assertEqual("S", jni_sig(jshort))
        self.assertEqual("Ljava/lang/Object;", jni_sig(Object))

        self.assertEqual("[Z", jni_sig(jarray(jboolean)))
        self.assertEqual("[[Z", jni_sig(jarray(jarray(jboolean))))

        self.assertEqual("[Ljava/lang/Object;", jni_sig(jarray(Object)))
        self.assertEqual("[[Ljava/lang/Object;", jni_sig(jarray(jarray(Object))))

        with self.assertRaisesRegex(ValueError, "Invalid JNI signature: 'java.lang.Object'"):
            jni_sig("java.lang.Object")

        for obj in [0, True, None, int, str]:
            with self.subTest(obj=obj):
                with self.assertRaisesRegex(TypeError, f"{obj!r} is not a Java type"):
                    jni_sig(obj)

    def test_jvoid(self):
        with self.assertRaisesRegex(TypeError, "Cannot create"):
            jvoid()

    # Tests for passing the wrappers to fields and methods are in test_conversion.
    def test_boolean(self):
        self.assertEqual("jboolean(True)", str(jboolean(True)))
        self.assertEqual("jboolean(True)", str(jboolean(42)))
        self.assertEqual("jboolean(True)", str(jboolean("hello")))
        self.assertEqual("jboolean(False)", str(jboolean("")))
        self.assertEqual("jboolean(False)", str(jboolean([])))

    def test_int(self):
        self.verify_int(jbyte, 8)
        self.verify_int(jshort, 16)
        self.verify_int(jint, 32)
        self.verify_int(jlong, 64)

    def verify_int(self, cls, bits):
        max_val = (2 ** (bits - 1)) - 1
        min_val = -max_val - 1

        for val in [min_val, max_val]:
            self.assertEqual("{}({})".format(cls.__name__, val),
                             str(cls(val)))

        for val in [min_val - 1, max_val + 1]:
            with self.too_big:
                cls(val)
            self.assertEqual("{}({})".format(cls.__name__, truncate(val, bits)),
                             str(cls(val, truncate=True)))

        with self.assertRaisesRegex(TypeError, "an integer is required"):
            cls("42")
        with self.assertRaisesRegex(TypeError, "an integer is required"):
            cls(42.0)
        with self.assertRaisesRegex(TypeError, "an integer is required"):
            cls(True)

    def test_float(self):
        self.verify_float(jfloat, 8)
        self.verify_float(jdouble, 11)

    def verify_float(self, cls, exponent_bits):
        max_exponent = (2 ** (exponent_bits - 1)) - 1
        max_val = 2.0 ** max_exponent
        min_val = -max_val

        for val in [42, 42.0, min_val, max_val, float("inf"), float("-inf"), float("nan")]:
            self.assertEqual("{}({})".format(cls.__name__, float(val)), str(cls(val)))

        if exponent_bits < 11:
            for val in [2.0 ** (max_exponent + 1),
                        -2.0 ** (max_exponent + 1)]:
                with self.too_big:
                    cls(val)
                self.assertEqual("{}({})".format(cls.__name__,
                                                 math.copysign(1, val) * float("inf")),
                                 str(cls(val, truncate=True)))

        with self.assertRaisesRegex(TypeError, "a float or integer is required"):
            cls("42")
        with self.assertRaisesRegex(TypeError, "a float or integer is required"):
            cls(True)

    def test_char(self):
        self.assertEqual("jchar('x')", str(jchar("x")))

        zhong_j = jchar("中")
        zhong_j_u = "jchar('中')"
        self.assertEqual(zhong_j_u, str(zhong_j))

        with self.assertRaisesRegex((TypeError, ValueError),
                                    r"(expected a character|only single character).*length 2"):
            jchar("ab")
        with self.assertRaisesRegex(TypeError, "non-BMP"):
            jchar("\U00010000")

    def test_array(self):
        list_bool = [True, False]
        for jarray_Z in [jarray(jboolean)(list_bool), jarray("Z")(list_bool)]:
            self.assertEqual("jarray('Z')", type(jarray_Z).__name__)
            self.assertEqual("jarray('Z')({!r})".format(list_bool), str(jarray_Z))

        list_list_bool = [[True, False], [False, True]]
        jarray_jarray_Z = jarray(jarray(jboolean))(list_list_bool)
        self.assertEqual("jarray('[Z')", type(jarray_jarray_Z).__name__)
        self.assertEqual("jarray('[Z')({!r})".format(list_list_bool), str(jarray_jarray_Z))

        list_str = ["one", "two"]
        String = jclass("java.lang.String")
        jarray_String = jarray(String)(list_str)
        self.assertEqual("jarray('Ljava/lang/String;')", type(jarray_String).__name__)
        self.assertEqual("jarray('Ljava/lang/String;')({!r})".format(list_str), str(jarray_String))


def truncate(value, bits):
    value &= (2 ** bits) - 1    # Remove high bits and map negative numbers to high positive ones
    value ^= 2 ** (bits - 1)    # Swap negatives and positives
    value -= 2 ** (bits - 1)    # Move everything back down to its proper place
    return value
