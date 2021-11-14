from contextlib import contextmanager, nullcontext
from java import jarray, jboolean, jbyte, jchar, jshort, jint, jlong, jfloat, jdouble
import unittest

try:
    from android.os import Build
except ImportError:
    Build = None


TEST_DATA = [2, 3, 5, 7]


class TestNumpy(unittest.TestCase):

    def test_basic(self):
        from numpy import array
        self.assertEqual([4, 7], (array([1, 2]) + array([3, 5])).tolist())

    def test_performance(self):
        import numpy as np
        from time import time

        start_time = time()
        SIZE = 500
        a = np.random.rand(SIZE, SIZE)
        b = np.random.rand(SIZE, SIZE)
        np.dot(a, b)

        # With OpenBLAS, the test devices take at most 0.4 seconds. Without OpenBLAS, they take
        # at least 1.0 seconds.
        duration = time() - start_time
        print(f"{duration:.3f}")
        self.assertLess(duration, 0.7)


# See also the "buffer" tests in runtime/src/test/python/chaquopy/test/test_array.py.
@unittest.skipUnless(Build, "Android only")
class TestNumpyJarray(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import numpy as np

        # np.intc and np.longlong correspond to buffer protocol formats "i" and "q"
        # (https://numpy.org/doc/stable/reference/arrays.scalars.html). np.int_ means C `long`
        # (buffer format "l"), which jarray never produces, but can accept. And the bit-width
        # names map to these as follows:
        #
        # * On 32-bit Unix, np.int_ is np.int32, np.longlong is np.int64, and np.intc is a
        #   separate type whose repr() is identical to np.int32.
        # * On 64-bit Unix, np,intc is np.int32, np.int_ is np.int64, and np.longlong is a
        #   separate type whose repr() is identical to np.int64.
        #
        # The identical repr() issue is fixed in Numpy 1.18
        # (https://github.com/numpy/numpy/issues/9799), but the types are still separate.
        long_itemsize = np.int_.itemsize

        cls.TESTS = []
        for element_type, dtype, values in \
            [(jboolean, np.bool_, [False, True]),
             (jbyte, np.int8, [-100, 0, 100]),
             (jshort, np.int16, [-10_000, 0, 10_000]),
             (jint, np.intc, [-1_000_000_000, 0, 1_000_000_000]),
             (jlong, np.longlong, [-1_000_000_000_000, 0, 1_000_000_000_000]),
             (jfloat, np.float32, [-float("inf"), -1.5, 0, 1.5, float("inf")]),
             (jdouble, np.float64, [-float("inf"), -1e300, 0, 1e300, float("inf")])]:
            cls.TESTS.append((element_type, dtype, dtype, values))
            if (element_type in [jint, jlong]) and (dtype().itemsize == long_itemsize):
                cls.TESTS.append((element_type, np.int_, dtype, values))

    def setUp(self):
        self.index_error = self.assertRaisesRegex(IndexError, "array index out of range")

    def test_1d(self):
        for *args, values in self.TESTS:
            with self.subTest(args=args):
                self.check_1d(*args, [])
                self.check_1d(*args, values)

    def check_1d(self, element_type, n2j_dtype, j2n_dtype, values):
        import numpy as np

        # NumPy to Java
        na = np.array(values, n2j_dtype)
        ja = jarray(element_type)(na)
        self.assertEqual(ja, na)
        if values:
            # This tests conversion from the NumPy scalar types
            # (https://numpy.org/doc/stable/reference/arrays.scalars.html), which in general do
            # not derive from the standard Python numeric types.
            self.assertNotEqual(ja[0], na[1])
            ja[0] = na[1]
            self.assertEqual(ja[0], na[1])

        # Java to NumPy
        ja = jarray(element_type)(values)
        na = np.array(ja)
        self.assertIs(j2n_dtype, na.dtype.type)
        self.assertEqual(ja, na)
        if values:
            self.assertNotEqual(na[0], ja[1])
            na[0] = ja[1]
            self.assertEqual(na[0], ja[1])

    def test_2d(self):
        import numpy as np

        for element_type, n2j_dtype, j2n_dtype, values in self.TESTS:
            with self.subTest(type=element_type):
                values_reversed = list(reversed(values))
                self.assertNotEqual(values, values_reversed)
                values_2d = [values, values_reversed]

                # NumPy to Java
                na = np.array(values_2d, n2j_dtype)
                ja = jarray(jarray(element_type))(na)
                self.assertEqual(ja, na)
                self.assertEqual(values, ja[0])
                self.assertEqual(values_reversed, ja[1])

                # Java to NumPy
                ja = jarray(jarray(element_type))(values_2d)
                na = np.array(ja)
                self.assertIs(j2n_dtype, na.dtype.type)
                self.assertEqual(ja, na)
                self.assertEqual(values, na[0].tolist())
                self.assertEqual(values_reversed, na[1].tolist())

    def test_scalar_get(self):
        from numpy import int32, float32
        arr = jarray(jint)(TEST_DATA)

        self.assertEqual(2, arr[int32(0)])
        self.assertEqual(3, arr[int32(1)])
        self.assertEqual(7, arr[int32(3)])
        with self.index_error:
            arr[int32(4)]

        self.assertEqual(7, arr[int32(-1)])
        self.assertEqual(5, arr[int32(-2)])
        self.assertEqual(2, arr[int32(-4)])
        with self.index_error:
            arr[int32(-5)]

        self.assertEqual([], arr[int32(0) : int32(0)])
        self.assertEqual([3, 5, 7], arr[int32(1):])
        self.assertEqual([3, 7], arr[int32(1)::int32(2)])
        self.assertEqual([2, 3, 5], arr[:int32(3)])
        self.assertEqual([2, 3], arr[int32(0) : int32(2)])
        self.assertEqual([3], arr[int32(1) : int32(2)])
        self.assertEqual([5, 3], arr[int32(2) : int32(0) : int32(-1)])

        with self.assertRaisesRegex(TypeError, r"array indices must be integers or slices, "
                                    r"not float32"):
            arr[float32(2)]
        with self.assertRaisesRegex(TypeError, r"slice indices must be integers or None or "
                                    r"have an __index__ method"):
            arr[float32(1) : float32(3)]

    def test_scalar_set(self):
        from numpy import int32, float32

        arr = jarray(jint)(TEST_DATA)
        arr[int32(0)] = 101
        arr[int32(1)] = 102
        arr[int32(3)] = 103
        self.assertEqual([101, 102, 5, 103], arr)
        with self.index_error:
            arr[int32(4)] = 99

        arr = jarray(jint)(TEST_DATA)
        arr[int32(-1)] = 201
        arr[int32(-2)] = 202
        arr[int32(-4)] = 203
        self.assertEqual([203, 3, 202, 201], arr)
        with self.index_error:
            arr[int32(-5)] = 99

        for slc, expected in [(slice(int32(0), int32(0)),               [2, 3, 5, 7]),
                              (slice(int32(1), None),                   [2, 0, 1, 2]),
                              (slice(int32(1), None, int32(2)),         [2, 0, 5, 1]),
                              (slice(None, int32(3)),                   [0, 1, 2, 7]),
                              (slice(int32(0), int32(2)),               [0, 1, 5, 7]),
                              (slice(int32(1), int32(2)),               [2, 0, 5, 7]),
                              (slice(int32(2), int32(0), int32(-1)),    [2, 1, 0, 7])]:
            with self.subTest(slc=slc):
                arr = jarray(jint)(TEST_DATA)
                arr[slc] = range(len(range(*slc.indices(len(TEST_DATA)))))
                self.assertEqual(expected, arr)

        arr = jarray(jint)(TEST_DATA)
        with self.assertRaisesRegex(ValueError, r"can't set slice of length 1 from value "
                                    r"of length 2"):
            arr[int32(1) : int32(2)] = [99, 99]
        with self.assertRaisesRegex(TypeError, r"array indices must be integers or slices, "
                                    r"not float32"):
            arr[float32(2)] = 99
        with self.assertRaisesRegex(TypeError, r"slice indices must be integers or None or "
                                    r"have an __index__ method"):
            arr[float32(1) : float32(3)] = [99, 99]
        self.assertEqual(TEST_DATA, arr)

    def test_method_arg(self):
        from java.lang import String
        import numpy as np
        from numpy.testing import assert_array_equal

        a_in = np.array(list(b'hello'), np.int8)
        s = String(a_in, "ASCII")
        self.assertEqual("hello", s)

        # This version of getBytes modifies its argument.
        a_out = np.zeros(5, np.int8)
        s.getBytes(0, 5, a_out, 0)
        assert_array_equal(a_out, a_in)

    def test_performance(self):
        import numpy as np

        SIZE = 1000000
        TIME_LIMIT = 0.5  # Without the buffer protocol, this takes over 10 seconds.
        for element_type, n2j_dtype, j2n_dtype, values in self.TESTS:
            # NumPy to Java
            na = np.zeros(SIZE, n2j_dtype)
            with self.assertTimeLimit(TIME_LIMIT):
                jarray(element_type)(na)

            na = np.zeros((2, SIZE // 2), n2j_dtype)
            with self.assertTimeLimit(TIME_LIMIT):
                jarray(jarray(element_type))(na)

            # Java to NumPy
            ja = jarray(element_type)(SIZE)
            with self.assertTimeLimit(TIME_LIMIT):
                na = np.array(ja)

            # Fast conversion of multi-dimensional arrays from Java to NumPy doesn't work yet.

    @contextmanager
    def assertTimeLimit(self, limit):
        from time import time
        start = time()
        yield
        self.assertLess(time() - start, limit)

    # It should be possible to initialize from different data types if and only if the values
    # could be assigned one element at a time.
    def test_different_dtype(self):
        import numpy as np

        for i, (element_type_small, dtype_small, _, values_small) in enumerate(self.TESTS):
            if element_type_small is jboolean:
                continue

            for (element_type_large, dtype_large, _, values_large) in self.TESTS[i + 1:]:
                with self.subTest(small=element_type_small, large=element_type_large):
                    compare = (np.testing.assert_allclose
                               if dtype_small == np.longlong and element_type_large == jfloat
                               else self.assertEqual)

                    # NumPy to Java
                    na = np.array(values_small, dtype_small)
                    ja = jarray(element_type_large)(na)
                    compare(ja, na)

                    def is_float_to_int(dtype, element_type):
                        return (issubclass(dtype, np.floating) and
                                element_type not in (jfloat, jdouble))

                    with (self.assertRaises(TypeError) if (
                            is_float_to_int(dtype_large, element_type_small))
                          else nullcontext()):
                        na = np.array(values_small, dtype_large)
                        compare(jarray(element_type_small)(na), na)

                    with self.assertRaises(
                            TypeError if is_float_to_int(dtype_large, element_type_small)
                            else OverflowError):
                        na = np.array(values_large, dtype_large)
                        jarray(element_type_small)(na)

                    # Java to NumPy
                    ja = jarray(element_type_small)(values_small)
                    compare(ja, np.array(ja, dtype_large))

        # Element assignment to NumPy arrays uses C casting rules.
        ja = jarray(jint)([126, 127, 128, 129])
        self.assertEqual([126, 127, -128, -127], np.array(ja, np.int8).tolist())
        ja = jarray(jint)([126, 127, -128, -127])
        self.assertEqual([126, 127, 128, 129], np.array(ja, np.uint8).tolist())
        ja = jarray(jfloat)([1.0, 1.1, 1.5, 1.9, 2.0, 2.1])
        self.assertEqual([1, 1, 1, 1, 2, 2], np.array(ja, np.int8).tolist())

    def test_char(self):
        import numpy as np

        ja = jarray(jchar)("hello")
        na = np.array(ja)
        self.assertEqual("<U1", na.dtype.str)
        self.assertEqual(ja, na)

        na = np.array(list("hello"))
        ja = jarray(jchar)(na)
        self.assertEqual(ja, na)

    def test_non_contiguous(self):
        import numpy as np

        a = np.array([[1, 2, 3], [4, 5, 6]])
        java_type = jarray(jarray(jdouble))
        self.assertEqual([[1, 2, 3], [4, 5, 6]], java_type(a))
        self.assertEqual([[1, 4], [2, 5], [3, 6]], java_type(a.T))
