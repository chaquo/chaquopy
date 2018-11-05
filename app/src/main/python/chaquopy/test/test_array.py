from __future__ import absolute_import, division, print_function

import ctypes
import sys
from java import cast, jarray, jboolean, jbyte, jchar, jclass, jint

from .test_utils import FilterWarningsCase


class TestArray(FilterWarningsCase):

    def test_basic(self):
        array_C = jarray(jchar)("hello")
        self.assertEqual(5, len(array_C))
        self.assertEqual(repr(array_C).replace("u'", "'"),
                         "jarray('C')(['h', 'e', 'l', 'l', 'o'])")

        self.assertTrue(isinstance(array_C, jclass("java.lang.Object")))
        self.assertTrue(isinstance(array_C, jclass("java.lang.Cloneable")))
        self.assertTrue(isinstance(array_C, jclass("java.io.Serializable")))
        self.assertFalse(isinstance(array_C, jclass("java.io.Closeable")))
        self.assertRegexpMatches(array_C.toString(), r"^\[C")

    def test_blank(self):
        array_Z = jarray(jboolean)(2)
        self.assertEqual(2, len(array_Z))
        self.assertEqual([False, False], array_Z)

        array_C = jarray(jchar)(3)
        self.assertEqual(3, len(array_C))
        self.assertEqual([u"\u0000", u"\u0000", u"\u0000"], array_C)

        array_I = jarray(jint)(2)
        self.assertEqual(2, len(array_I))
        self.assertEqual([0, 0], array_I)

        from java.lang import Object
        array_Object = jarray(Object)(3)
        self.assertEqual(3, len(array_Object))
        self.assertEqual([None, None, None], array_Object)

        array_empty = jarray(Object)(0)
        self.assertEqual(0, len(array_empty))
        self.assertEqual([], array_empty)

    # More conversion tests in test_conversion.py
    def test_conversion(self):
        Object = jclass("java.lang.Object")
        Integer = jclass("java.lang.Integer")
        TestArray = jclass('com.chaquo.python.TestArray')
        # All object arrays, primitive arrays, and Python iterables are assignable to Object,
        # Cloneable and Serializable
        for array in [jarray(Object)(["hello", 42]), jarray(Integer)([11, 22]),
                      jarray(jboolean)([False, True]), [False, True]]:
            for field in ["object", "cloneable", "serializable"]:
                setattr(TestArray, field, array)
                self.assertEqual(array, getattr(TestArray, field))
                with self.assertRaisesRegexp(TypeError, "Cannot convert"):
                    setattr(TestArray, "closeable", array)

    def test_cast(self):
        Object = jclass("java.lang.Object")
        Boolean = jclass("java.lang.Boolean")

        Boolean_array = jarray(Boolean)([True, False])
        Boolean_array_Object_array = cast(jarray(Object), Boolean_array)
        self.assertIsNot(Boolean_array, Boolean_array_Object_array)
        self.assertEqual(Boolean_array, Boolean_array_Object_array)
        self.assertIs(Boolean_array_Object_array, cast(jarray(Object), Boolean_array))
        self.assertIs(Boolean_array, cast(jarray(Boolean), Boolean_array_Object_array))

        Boolean_array_Object = cast(Object, Boolean_array)
        self.assertIsNot(Boolean_array, Boolean_array_Object)
        self.assertEqual(Boolean_array, Boolean_array_Object)
        self.assertIs(Boolean_array_Object, cast(Object, Boolean_array))
        self.assertIs(Boolean_array, cast(jarray(Boolean), Boolean_array_Object))

        with self.assertRaisesRegexp(TypeError, r"cannot create boolean\[\] proxy from "
                                     r"java.lang.Boolean\[\] instance"):
            cast(jarray(jboolean), Boolean_array)

        with self.assertRaisesRegexp(TypeError, r"cannot create java.lang.Object\[\] proxy from "
                                     "java.lang.Object instance"):
            cast(jarray(Object), Object())

        Object_array = jarray(Object)([])
        with self.assertRaisesRegexp(TypeError, r"cannot create java.lang.Boolean proxy from "
                                     r"java.lang.Object\[\] instance"):
            cast(Boolean, Object_array)
        with self.assertRaisesRegexp(TypeError, r"cannot create java.lang.Boolean\[\] proxy from "
                                     r"java.lang.Object\[\] instance"):
            cast(jarray(Boolean), Object_array)

        Z_array = jarray(jboolean)([True, False])
        with self.assertRaisesRegexp(TypeError, r"cannot create java.lang.Boolean\[\] proxy from "
                                     r"boolean\[\] instance"):
            cast(jarray(Boolean), Z_array)
        with self.assertRaisesRegexp(TypeError, r"cannot create java.lang.Object\[\] proxy from "
                                     r"boolean\[\] instance"):
            cast(jarray(Object), Z_array)

    def test_output_arg(self):
        String = jclass('java.lang.String')
        string = String(u'\u1156\u2278\u3390\u44AB')
        for btarray in ([0] * 4,
                        (0,) * 4,
                        jarray(jbyte)([0] * 4)):
            # This version of getBytes returns the 8 low-order of each Unicode character.
            string.getBytes(0, 4, btarray, 0)
            if not isinstance(btarray, tuple):
                self.assertEquals(btarray, [ctypes.c_int8(x).value
                                            for x in [0x56, 0x78, 0x90, 0xAB]])

    def test_multiple_dimensions(self):
        Arrays = jclass('com.chaquo.python.TestArray')
        matrix = [[1, 2, 3],
                  [4, 5, 6],
                  [7, 8, 9]]
        self.assertEquals(Arrays.methodParamsMatrixI(matrix), True)
        self.assertEquals(Arrays.methodReturnMatrixI(), matrix)

    # Most of the positive tests are in test_conversion, but here are some error tests.
    def test_modify(self):
        Object = jclass("java.lang.Object")
        array_Z = jarray(jboolean)([True, False])
        with self.assertRaisesRegexp(TypeError, "Cannot convert int object to boolean"):
            array_Z[0] = 1
        with self.assertRaisesRegexp(TypeError, "Cannot convert Object object to boolean"):
            array_Z[0] = Object()

        Boolean = jclass("java.lang.Boolean")
        array_Boolean = jarray(Boolean)([True, False])
        with self.assertRaisesRegexp(TypeError, "Cannot convert int object to java.lang.Boolean"):
            array_Boolean[0] = 1
        with self.assertRaisesRegexp(TypeError, "Cannot convert int object to java.lang.Boolean"):
            cast(jarray(Object), array_Boolean)[0] = 1

        array_Object = jarray(Object)([True, False])
        array_Object[0] = 1
        self.assertEqual([1, False], array_Object)

    def test_str_repr(self):
        Object = jclass("java.lang.Object")
        for func in [str, repr]:
            self.assertEqual("cast('[Z', None)", func(cast(jarray(jboolean), None)))
            self.assertEqual("cast('[[Z', None)", func(cast(jarray(jarray(jboolean)), None)))
            self.assertEqual("cast('[Ljava/lang/Object;', None)",
                             func(cast(jarray(Object), None)))
            self.assertEqual("cast('[[Ljava/lang/Object;', None)",
                             func(cast(jarray(jarray(Object)), None)))

            self.assertEqual("jarray('Z')([])", func(jarray(jboolean)([])))
            self.assertEqual("jarray('Ljava/lang/Object;')([])", func(jarray(Object)([])))

            self.assertEqual("jarray('Z')([True])", func(jarray(jboolean)([True])))
            self.assertEqual("jarray('Z')([True])", func(jarray(jboolean)((True,))))
            self.assertEqual("jarray('Z')([True, False])", func(jarray(jboolean)([True, False])))
            self.assertEqual("jarray('[Z')([[True], [False, True]])",
                             func(jarray(jarray(jboolean))([[True], [False, True]])))

    def test_bytes(self):
        self.verify_bytes([], b"")
        self.verify_bytes([-128, -127, -2, -1, 0, 1, 2, 126, 127],
                          b"\x80\x81\xFE\xFF\x00\x01\x02\x7E\x7F")

        # These optional arguments are not part of the public API and are subject to change.
        array_B = jarray(jbyte)([0, 102, 111, 111, 127, -1, -128])
        self.assertEqual(b"\x00foo\x7F\xFF\x80", array_B.__bytes__())
        self.assertEqual(b"foo", array_B.__bytes__(1, 3))
        self.assertEqual(b"\xFF\x80", array_B.__bytes__(5))
        self.assertEqual(b"\x00foo", array_B.__bytes__(length=4))

    def verify_bytes(self, jbyte_values, b):
        arrayB_from_list = jarray(jbyte)(jbyte_values)
        self.assertEqual(jbyte_values, arrayB_from_list)

        to_bytes = (bytes if sys.version_info[0] >= 3
                    else lambda x: x.__bytes__())
        array_bytes = to_bytes(arrayB_from_list)
        self.assertIsInstance(array_bytes, bytes)
        self.assertEqual(b, array_bytes)
        # TODO #5231: use `bytearray(bytes(...))` instead.
        # array_bytearray = bytearray(arrayB_from_list)
        # self.assertEqual(b, array_bytearray)

        arrayB_from_bytes = jarray(jbyte)(b)
        self.assertEqual(jbyte_values, arrayB_from_bytes)
        arrayB_from_bytearray = jarray(jbyte)(bytearray(b))
        self.assertEqual(jbyte_values, arrayB_from_bytearray)

        b_as_ints = b if (sys.version_info[0] >= 3) else map(ord, b)
        arrayI_from_bytes = jarray(jint)(b_as_ints)
        self.assertEqual(b_as_ints, arrayI_from_bytes)
        with self.assertRaisesRegexp(TypeError, "Cannot call __bytes__ on int[], only on byte[]"):
            to_bytes(arrayI_from_bytes)

    def test_eq(self):
        tf = jarray(jboolean)([True, False])
        self.verify_equal(tf, tf)
        self.verify_equal(tf, jarray(jboolean)([True, False]))
        self.verify_equal(tf, [True, False])
        self.verify_equal(tf, [1, 0])

        self.verify_not_equal(tf, [True, True])
        self.verify_not_equal(tf, [True, False, True])

        single = jarray(jboolean)([True])
        self.verify_not_equal(single, True)

        empty = jarray(jboolean)([])
        self.verify_equal(empty, empty)
        self.verify_equal(empty, [])
        self.verify_not_equal(empty, single)
        self.verify_not_equal(empty, False)

    def verify_equal(self, a, b):
        self.assertEqual(a, b)
        self.assertEqual(b, a)
        self.assertFalse(a != b)
        self.assertFalse(b != a)

    def verify_not_equal(self, a, b):
        self.assertNotEqual(a, b)
        self.assertNotEqual(b, a)
        self.assertFalse(a == b)
        self.assertFalse(b == a)

    def test_hash(self):
        with self.assertRaisesRegexp(TypeError, "unhashable type"):
            hash(jarray(jboolean)([]))

    def test_add(self):
        tf = jarray(jboolean)([True, False])
        self.assertEqual(tf, tf + [])
        self.assertEqual(tf, [] + tf)
        self.assertEqual(tf, tf + jarray(jboolean)([]))
        self.assertEqual([True, False, True], tf + [True])
        with self.assertRaises(TypeError):
            tf + True
        with self.assertRaises(TypeError):
            tf + None

        String = jclass("java.lang.String")
        hw = jarray(String)(["hello", "world"])
        self.assertEqual([True, False, "hello", "world"], tf + hw)

    def test_iter(self):
        a = jarray(jint)([1, 2, 3])
        self.assertEqual([1, 2, 3], [x for x in a])

    def test_in(self):
        a = jarray(jint)([1, 2])
        self.assertTrue(1 in a)
        self.assertTrue(2 in a)
        self.assertFalse(3 in a)

    def test_attributes(self):
        a = jarray(jint)([1, 2, 3])
        with self.assertRaises(AttributeError):
            a.length
        with self.assertRaises(AttributeError):
            a.foo = 99
