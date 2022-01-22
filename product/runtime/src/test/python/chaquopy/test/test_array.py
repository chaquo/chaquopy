import copy
import ctypes
from java import (cast, jarray, jboolean, jbyte, jchar, jclass, jdouble, jfloat, jint,
                  jlong, jshort)
import pickle
from .test_utils import FilterWarningsCase

from com.chaquo.python import TestArray as TA
from java.lang import String, System


# In order for test_set_slice to work, all elements must be different.
SLICE_DATA = [2, 3, 5, 7, 11]

SLICE_TESTS = [
    # Basic
    (slice(0, 1), [2]),
    (slice(0, 2), [2, 3]),
    (slice(0, 5), [2, 3, 5, 7, 11]),
    (slice(1, 2), [3]),
    (slice(1, 3), [3, 5]),

    (slice(-5, -4), [2]),
    (slice(-5, -3), [2, 3]),
    (slice(-5, 5), [2, 3, 5, 7, 11]),
    (slice(-4, -3), [3]),
    (slice(-4, -2), [3, 5]),

    # Open-ended
    (slice(None, None), [2, 3, 5, 7, 11]),
    (slice(0, None), [2, 3, 5, 7, 11]),
    (slice(None, 1), [2]),
    (slice(None, 2), [2, 3]),
    (slice(1, None), [3, 5, 7, 11]),

    (slice(-5, None), [2, 3, 5, 7, 11]),
    (slice(None, -4), [2]),
    (slice(None, -3), [2, 3]),
    (slice(-4, None), [3, 5, 7, 11]),

    # Truncated
    (slice(2, 6), [5, 7, 11]),
    (slice(-6, -2), [2, 3, 5]),

    # Empty
    (slice(0, 0), []),
    (slice(1, 1), []),
    (slice(1, 0), []),

    (slice(-5, -5), []),
    (slice(-4, -4), []),
    (slice(-4, -5), []),

    # Non-contiguous
    (slice(None, None, 2), [2, 5, 11]),
    (slice(1, None, 2), [3, 7]),
    (slice(1, 3, 2), [3]),
    (slice(None, None, 3), [2, 7]),
    (slice(None, None, 4), [2, 11]),
    (slice(None, None, 5), [2]),

    (slice(-4, None, 2), [3, 7]),
    (slice(-4, -2, 2), [3]),

    # Reversed
    (slice(None, None, -1), [11, 7, 5, 3, 2]),
    (slice(None, None, -2), [11, 5, 2]),
    (slice(3, None, -2), [7, 3]),
    (slice(0, None, -1), [2]),
    (slice(1, None, -1), [3, 2]),
    (slice(4, 2, -1), [11, 7]),

    (slice(-2, None, -2), [7, 3]),
    (slice(-5, None, -1), [2]),
    (slice(-4, None, -1), [3, 2]),
    (slice(-1, -3, -1), [11, 7]),
]


class TestArray(FilterWarningsCase):
    from .test_utils import assertTimeLimit

    def setUp(self):
        super().setUp()
        self.index_error = self.assertRaisesRegex(IndexError, "array index out of range")

    def test_basic(self):
        array_cls = jarray(jchar)
        self.assertEqual("java", array_cls.__module__)
        self.assertEqual("jarray('C')", array_cls.__name__)
        self.assertEqual(array_cls.__name__, array_cls.__qualname__)

        array_C = array_cls("hello")
        self.assertEqual(5, len(array_C))
        self.assertEqual(repr(array_C), "jarray('C')(['h', 'e', 'l', 'l', 'o'])")

        self.assertTrue(isinstance(array_C, jclass("java.lang.Object")))
        self.assertTrue(isinstance(array_C, jclass("java.lang.Cloneable")))
        self.assertTrue(isinstance(array_C, jclass("java.io.Serializable")))
        self.assertFalse(isinstance(array_C, jclass("java.io.Closeable")))
        self.assertRegex(array_C.toString(), r"^\[C")

    def test_type_klass(self):
        self.assertIs(jarray(String), jarray(String.getClass()))

    def test_type_jni(self):
        self.assertIs(jarray(String), jarray("Ljava/lang/String;"))

        with self.assertRaisesRegex(jclass("java.lang.NoClassDefFoundError"),
                                    "java.lang.Nonexistent"):
            jarray("Ljava/lang/Nonexistent;")

        with self.assertRaisesRegex(ValueError, "Invalid JNI signature: 'java.lang.String'"):
            jarray("java.lang.String")

    def test_type_invalid(self):
        for element_type in [0, True, None, int, str]:
            with self.subTest(element_type=element_type):
                with self.assertRaisesRegex(TypeError, f"{element_type!r} is not a Java type"):
                    jarray(element_type)

    def test_blank(self):
        array_Z = jarray(jboolean)(2)
        self.assertEqual(2, len(array_Z))
        self.assertEqual([False, False], array_Z)

        array_C = jarray(jchar)(3)
        self.assertEqual(3, len(array_C))
        self.assertEqual(["\u0000", "\u0000", "\u0000"], array_C)

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
        # All object arrays, primitive arrays, and Python iterables are assignable to Object,
        # Cloneable and Serializable
        for array in [jarray(Object)(["hello", 42]), jarray(Integer)([11, 22]),
                      jarray(jboolean)([False, True]), [False, True]]:
            with self.subTest(array=array):
                for field in ["object", "cloneable", "serializable"]:
                    with self.subTest(field=field):
                        setattr(TA, field, array)
                        self.assertEqual(array, getattr(TA, field))
                with self.assertRaisesRegex(TypeError, "Cannot convert"):
                    setattr(TA, "closeable", array)

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

        with self.assertRaisesRegex(TypeError, r"cannot create boolean\[\] proxy from "
                                    r"java.lang.Boolean\[\] instance"):
            cast(jarray(jboolean), Boolean_array)

        with self.assertRaisesRegex(TypeError, r"cannot create java.lang.Object\[\] proxy from "
                                    "java.lang.Object instance"):
            cast(jarray(Object), Object())

        Object_array = jarray(Object)([])
        with self.assertRaisesRegex(TypeError, r"cannot create java.lang.Boolean proxy from "
                                    r"java.lang.Object\[\] instance"):
            cast(Boolean, Object_array)
        with self.assertRaisesRegex(TypeError, r"cannot create java.lang.Boolean\[\] proxy from "
                                    r"java.lang.Object\[\] instance"):
            cast(jarray(Boolean), Object_array)

        Z_array = jarray(jboolean)([True, False])
        with self.assertRaisesRegex(TypeError, r"cannot create java.lang.Boolean\[\] proxy from "
                                    r"boolean\[\] instance"):
            cast(jarray(Boolean), Z_array)
        with self.assertRaisesRegex(TypeError, r"cannot create java.lang.Object\[\] proxy from "
                                    r"boolean\[\] instance"):
            cast(jarray(Object), Z_array)

    def test_output_arg(self):
        string = String('\u1156\u2278\u3390\u44AB')
        for btarray in ([0] * 4,
                        (0,) * 4,
                        jarray(jbyte)([0] * 4)):
            # This version of getBytes returns the 8 low-order of each Unicode character.
            string.getBytes(0, 4, btarray, 0)
            if not isinstance(btarray, tuple):
                self.assertEqual(btarray, [ctypes.c_int8(x).value
                                           for x in [0x56, 0x78, 0x90, 0xAB]])

        for method in ["arraySort", "arraySortObject"]:
            for input in [[], [42], [5, 7, 2, 11, 3]]:
                with self.subTest(method=method, input=input):
                    l = input.copy()
                    getattr(TA, method)(l)
                    self.assertEqual(sorted(input), l)

    def test_multiple_dimensions(self):
        matrix = [[1, 2, 3],
                  [4, 5, 6],
                  [7, 8, 9]]
        self.assertEqual(TA.methodParamsMatrixI(matrix), True)
        self.assertEqual(TA.methodReturnMatrixI(), matrix)

    def test_get_int(self):
        a = jarray(jint)([2, 3, 5, 7, 11])

        self.assertEqual(2, a[0])
        self.assertEqual(3, a[1])
        self.assertEqual(11, a[4])
        with self.index_error:
            a[5]
        with self.index_error:
            jarray(jint)([])[0]

        self.assertEqual(11, a[-1])
        self.assertEqual(7, a[-2])
        self.assertEqual(2, a[-5])
        with self.index_error:
            a[-6]

    def test_set_int(self):
        a = jarray(jint)([2, 3, 5, 7, 11])

        a[0] = 0
        a[1] = 10
        a[4] = 40
        self.assertEqual([0, 10, 5, 7, 40], a)
        with self.index_error:
            a[5] = 50
        with self.index_error:
            jarray(jint)([])[0] = 99

        a[-1] = -10
        a[-2] = -20
        a[-5] = -50
        self.assertEqual([-50, 10, 5, -20, -10], a)
        with self.index_error:
            a[-6] = -60

    def test_get_slice(self):
        a = jarray(jint)(SLICE_DATA)
        for key, expected in SLICE_TESTS:
            actual = a[key]
            self.assertIsInstance(actual, jarray(jint))
            self.assertEqual(expected, actual)

        # Without optimization, this takes over 5 seconds.
        a = jarray(jint)(500000)
        with self.assertTimeLimit(0.5):
            self.assertIsNot(a[:], a)

    def test_copy_method(self):
        for data in [[], SLICE_DATA]:
            with self.subTest(data=data):
                a = jarray(jint)(data)
                self.check_copy_1d(a, a.copy(), identical=False)

        a = jarray(jarray(jint))([[], SLICE_DATA])
        a_copy = a.copy()
        self.check_copy_2d(a, a_copy, deep=False)

    # TODO: if we implement __deepcopy__, it should succeed if and only if the innermost
    # element type is primitive, because non-array Java objects are uncopyable (see
    # TestReflect.test_pickle). Because of this, deepcopying a recursive array is impossible,
    # because the innermost element type would have to be Object. However, we should still test
    # arrays containing some nulls.
    def test_copy_module(self):
        for data in [[], SLICE_DATA]:
            with self.subTest(data=data):
                a = jarray(jint)(data)
                self.check_copy_1d(a, copy.copy(a), identical=False)

        a = jarray(jarray(jint))([[], SLICE_DATA])
        a_copy = copy.copy(a)
        self.check_copy_2d(a, a_copy, deep=False)

    def check_copy_1d(self, a, a_copy, *, identical):
        self.assertIs(type(a_copy), type(a))
        self.assertEqual(a_copy, a)
        (self.assertIs if identical else self.assertIsNot)(
            a_copy, a)
        (self.assertEqual if identical else self.assertNotEqual)(
            System.identityHashCode(a_copy), System.identityHashCode(a))

    def check_copy_2d(self, a, a_copy, *, deep):
        self.check_copy_1d(a, a_copy, identical=False)
        for i, x in enumerate(a):
            x_copy = a_copy[i]
            self.check_copy_1d(x, x_copy, identical=not deep)

    def test_pickle(self):
        for data in [[], SLICE_DATA]:
            for function in [pickle.dumps, copy.deepcopy]:
                with self.subTest(data=data, function=function.__name__), \
                     self.assertRaisesRegex(pickle.PicklingError,
                                            "Java objects cannot be pickled"):
                    a = jarray(jint)(data)
                    function(a)

    def test_set_slice(self):
        for key, replaced in SLICE_TESTS:
            with self.subTest(key=key, replaced=replaced):
                a = jarray(jint)(SLICE_DATA)
                expected = [99 if x in replaced else x
                            for x in a]
                a[key] = [99] * len(replaced)
                self.assertEqual(expected, a)

        # Length mismatch
        a = jarray(jint)(SLICE_DATA)
        for value in [[], [99, 99]]:
            with self.subTest(value=value), \
                 self.assertRaisesRegex(ValueError, f"can't set slice of length 1 from value "
                                        f"of length {len(value)}"):
                a[0:1] = value

        # Arrays of different types.
        a = jarray(jint)(SLICE_DATA)
        with self.assertRaisesRegex(TypeError, "Cannot convert float object to int"):
            a[:2] = jarray(jfloat)([99, 99])

        a = jarray(jfloat)(SLICE_DATA)
        a[:2] = jarray(jint)([99, 99])
        self.assertEqual([99, 99, 5, 7, 11], a)

        # Without optimization, this takes over 200 seconds. The test_get_slice equivalent is
        # probably faster because Cython compiles the __getitem__ loop into native code, so
        # leave the array size unchanged in case a future Cython version extends this to more
        # situations.
        a = jarray(jint)(500000)
        b = jarray(jint)(500000)
        with self.assertTimeLimit(0.5):
            a[:] = b

    def test_invalid_index(self):
        a = jarray(jint)(SLICE_DATA)
        for index in ["", "hello", 0.0, 1.0]:
            with self.subTest(index=index):
                error = self.assertRaisesRegex(
                    TypeError, fr"array indices must be integers or slices, not "
                    fr"{type(index).__name__}")
                with error:
                    a[index]
                with error:
                    a[index] = 99
                self.assertEqual(SLICE_DATA, a)

    # Most of the positive tests are in test_conversion, but here are some error tests.
    def test_modify(self):
        Object = jclass("java.lang.Object")
        array_Z = jarray(jboolean)([True, False])
        with self.assertRaisesRegex(TypeError, "Cannot convert int object to boolean"):
            array_Z[0] = 1
        with self.assertRaisesRegex(TypeError, "Cannot convert Object object to boolean"):
            array_Z[0] = Object()

        Boolean = jclass("java.lang.Boolean")
        array_Boolean = jarray(Boolean)([True, False])
        with self.assertRaisesRegex(TypeError, "Cannot convert int object to java.lang.Boolean"):
            array_Boolean[0] = 1
        with self.assertRaisesRegex(TypeError, "Cannot convert int object to java.lang.Boolean"):
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
        # Java byte arrays (signed) and Python bytes (unsigned) can be converted both ways.
        self.verify_bytes([], b"")
        self.verify_bytes([-128, -127, -2, -1, 0, 1, 126, 127],
                          b"\x80\x81\xFE\xFF\x00\x01\x7E\x7F")

        # Java primitive arrays (except char[]) can be converted to their raw data bytes.
        # Expected values are little-endian.
        for element_type, values, expected in \
            [(jboolean, [False, True], b"\x00\x01"),
             (jbyte, [0, 123], bytes(1) + b"\x7b"),
             (jshort, [0, 12345], bytes(2) + b"\x39\x30"),
             (jint, [0, 123456789], bytes(4) + b"\x15\xcd\x5b\x07"),
             (jlong, [0, 1234567890123456789], bytes(8) + b"\x15\x81\xe9\x7d\xf4\x10\x22\x11"),
             (jfloat, [0, 1.99], bytes(4) + b"\x52\xb8\xfe\x3f"),
             (jdouble, [0, 1.99], bytes(8) + b"\xd7\xa3\x70\x3d\x0a\xd7\xff\x3f")]:
            java_type = jarray(element_type)
            for python_type in [bytes, bytearray]:
                with self.subTest(element_type=element_type, python_type=python_type):
                    self.assertEqual(b"", python_type(java_type([])))
                    self.assertEqual(expected, python_type(java_type(values)))

        # Integer arrays containing values 0 to 255 can be converted element-wise using `list`.
        for element_type in [jshort, jint, jlong]:
            with self.subTest(element_type=element_type):
                self.assertEqual(
                    b"\x00\x01\x7E\x7F\x80\x81\xFE\xFF",
                    bytes(list(jarray(element_type)([0, 1, 126, 127, 128, 129, 254, 255]))))

        # Other array types (including multi-dimensional arrays) will be treated as an iterable
        # of integers, so converting them to bytes will fail unless the array is empty.
        for element_type, values in \
            [(jchar, "hello"),
             (jarray(jbyte), [b"hello", b"world"]),
             (String, ["hello"])]:
            java_type = jarray(element_type)
            for python_type in [bytes, bytearray]:
                with self.subTest(element_type=element_type, python_type=python_type):
                    self.assertEqual(b"", python_type(java_type([])))
                    with self.assertRaisesRegex(TypeError, "cannot be interpreted as an integer"):
                        python_type(java_type(values))

    def verify_bytes(self, jbyte_values, b):
        arrayB_from_list = jarray(jbyte)(jbyte_values)
        self.assertEqual(jbyte_values, arrayB_from_list)

        array_bytes = bytes(arrayB_from_list)
        self.assertEqual(b, array_bytes)
        array_bytearray = bytearray(arrayB_from_list)
        self.assertEqual(b, array_bytearray)

        arrayB_from_bytes = jarray(jbyte)(b)
        self.assertEqual(jbyte_values, arrayB_from_bytes)
        arrayB_from_bytearray = jarray(jbyte)(bytearray(b))
        self.assertEqual(jbyte_values, arrayB_from_bytearray)

    BUFFER_TESTS = [
        (jboolean, "?", 1, [True, False]),
        (jbyte, "b", 1, [-100, 0, 100]),
        (jshort, "h", 2, [-10_000, 0, 10_000]),
        (jint, "i", 4, [-1_000_000_000, 0, 1_000_000_000]),
        (jlong, "q", 8, [-1_000_000_000_000, 0, 1_000_000_000_000]),
        (jfloat, "f", 4, [-float("inf"), -1.5, 0, 1.5, float("inf")]),
        (jdouble, "d", 8, [-float("inf"), -1e300, 0, 1e300, float("inf")])]

    # See also the NumPy package tests.
    def test_buffer_j2p(self):
        for element_type, format, itemsize, values in self.BUFFER_TESTS:
            for input in [[], values]:
                with self.subTest(element_type=element_type, input=input):
                    ja = jarray(element_type)(input)
                    m = memoryview(ja)
                    self.assertEqual(input, m.tolist())
                    self.assertEqual(len(input) * itemsize, m.nbytes)
                    self.assertFalse(m.readonly)
                    self.assertEqual(format, m.format)
                    self.assertEqual(itemsize, m.itemsize)
                    self.assertEqual(1, m.ndim)
                    self.assertEqual((len(input),), m.shape)
                    self.assertEqual((itemsize,), m.strides)
                    self.assertEqual((), m.suboffsets)
                    self.assertTrue(m.c_contiguous)

                    # Because the JVM may return a copy, we can't guarantee that updates to the
                    # view will be written to the array until the view is released, and we
                    # can't guarantee that updates to the array are ever visible to the view.
                    if ja:
                        self.assertNotEqual(ja[0], ja[1])
                        m[0] = m[1]
                        self.assertEqual(m[0], m[1])
                        m.release()
                        self.assertEqual(ja[0], ja[1])

        for element_type in [jchar, jarray(jbyte), String]:
            with self.assertRaisesRegex(TypeError, "a bytes-like object is required"):
                memoryview(jarray(element_type)([]))

    # See also the NumPy package tests.
    def test_buffer_p2j(self):
        import array
        sizeof_long = array.array("l").itemsize  # May be 4 or 8.

        for element_type, format, itemsize, values in self.BUFFER_TESTS:
            if element_type is jboolean:
                # array.array doesn't support this format, but it's covered by the NumPy tests.
                continue
            for input in [[], values]:
                with self.subTest(element_type=element_type, input=input):
                    self.check_buffer_p2j(element_type, format, input)
                    if (format in "iq") and (itemsize == sizeof_long):
                        self.check_buffer_p2j(element_type, "l", input)

    def check_buffer_p2j(self, element_type, format, input):
        import array
        aa = array.array(format, input)
        ja = jarray(element_type)(aa)
        self.assertEqual(ja, aa)

    def test_abc(self):
        from collections import abc
        for element_type in [jboolean, jbyte, jshort, jint, jlong, jfloat, jdouble, jchar,
                             String, jarray(String)]:
            with self.subTest(element_type=element_type):
                a = jarray(element_type)([])
                self.assertIsInstance(a, abc.Sequence)
                self.assertNotIsInstance(a, abc.MutableSequence)
                for method in ["__getitem__", "__len__", "__contains__", "__iter__",
                               "__reversed__", "index", "count"]:
                    with self.subTest(method=method):
                        self.assertTrue(hasattr(a, method))

    def test_truth(self):
        self.assertFalse(jarray(jboolean)([]))
        self.assertTrue(jarray(jboolean)([False]))
        self.assertTrue(jarray(jboolean)([True]))

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
        with self.assertRaisesRegex(TypeError, "unhashable type"):
            hash(jarray(jboolean)([]))

    def test_add(self):
        tf = jarray(jboolean)([True, False])
        self.assertEqual(tf, tf + [])
        self.assertEqual(tf, [] + tf)
        self.assertEqual(tf, tf + jarray(jboolean)([]))
        self.assertEqual([True, False, True, False], tf + tf)
        self.assertEqual([True, False, True], tf + [True])
        self.assertEqual([True, True, False], [True] + tf)
        with self.assertRaises(TypeError):
            tf + True
        with self.assertRaises(TypeError):
            tf + None

        hw = jarray(String)(["hello", "world"])
        self.assertEqual([True, False, "hello", "world"], tf + hw)

    def test_contains(self):
        a = jarray(jint)([1, 4, 1, 2])
        self.assertFalse(0 in a)
        self.assertTrue(1 in a)
        self.assertTrue(2 in a)
        self.assertFalse(3 in a)
        self.assertTrue(4 in a)
        self.assertFalse(5 in a)

        empty = jarray(jint)([])
        self.assertFalse(0 in empty)
        self.assertFalse(1 in empty)

    def test_iter(self):
        for data in [[], [1], [2, 3], [4, 5, 6]]:
            with self.subTest(data=data):
                a = jarray(jint)(data)
                self.assertEqual(data, [x for x in a])

    def test_reversed(self):
        for data in [[], [1], [2, 3], [4, 5, 6]]:
            with self.subTest(data=data):
                a = jarray(jint)(data)
                self.assertEqual(list(reversed(data)), list(reversed(a)))

    def test_index(self):
        a = jarray(jint)([1, 4, 1, 2])
        self.assertEqual(0, a.index(1))
        self.assertEqual(3, a.index(2))
        self.assertEqual(1, a.index(4))
        for value in [0, 3, 5]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    a.index(value)

        empty = jarray(jint)([])
        for value in [0, 1]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    empty.index(value)

    def test_count(self):
        a = jarray(jint)([1, 4, 1, 2])
        self.assertEqual(0, a.count(0))
        self.assertEqual(2, a.count(1))
        self.assertEqual(1, a.count(2))
        self.assertEqual(0, a.count(3))
        self.assertEqual(1, a.count(4))
        self.assertEqual(0, a.count(5))

        empty = jarray(jint)([])
        self.assertEqual(0, empty.count(0))
        self.assertEqual(0, empty.count(1))

    def test_attributes(self):
        a = jarray(jint)([1, 2, 3])
        with self.assertRaises(AttributeError):
            a.length
        with self.assertRaises(AttributeError):
            a.foo = 99
