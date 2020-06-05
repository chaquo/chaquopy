import unittest

try:
    from android.os import Build
except ImportError:
    Build = None


class TestNumpy(unittest.TestCase):

    def test_basic(self):
        from numpy import array
        self.assertEqual([4, 7], (array([1, 2]) + array([3, 5])).tolist())

    # This will probably fail if optimized BLAS is not being used.
    def test_performance(self):
        import numpy as np
        from time import time

        start_time = time()
        SIZE = 500
        a = np.random.rand(SIZE, SIZE)
        b = np.random.rand(SIZE, SIZE)
        np.dot(a, b)
        self.assertLess(time() - start_time, 1)

    @unittest.skipUnless(Build, "Android only")
    def test_jarray(self):
        from java import jarray, jbyte, jshort, jint, jlong, jfloat, jdouble
        import numpy as np

        # We use np.intc and np.longlong, because they correspond to buffer protocol formats
        # "i" and "q" (https://numpy.org/doc/stable/reference/arrays.scalars.html). The other
        # types are inconsistent (https://github.com/numpy/numpy/issues/9799):
        #
        # * On 32-bit platforms, np.int_ is np.int32, np.longlong is np.int64, and np.intc is a
        #   separate type whose repr() is identical to np.int32.
        # * On 64-bit platforms, np,intc is np.int32, np.int_ is np.int64, and np.longlong is a
        #   separate type whose repr() is identical to np.int64.
        #
        # The identical repr() issue is fixed in Numpy 1.18, but the types are still separate.
        for java_type, dtype, values in \
            [(jbyte, np.int8, [-100, 0, 100]),
             (jshort, np.int16, [-10_000, 0, 10_000]),
             (jint, np.intc, [-1_000_000_000, 0, 1_000_000_000]),
             (jlong, np.longlong, [-1_000_000_000_000, 0, 1_000_000_000_000]),
             (jfloat, np.float32, [-float("inf"), -1.5, 0, 1.5, float("inf")]),
             (jdouble, np.float64, [-float("inf"), -1e300, 0, 1e300, float("inf")])]:
            for input in [[], values]:
                with self.subTest(java_type=java_type, input=input):
                    ja = jarray(java_type)(input)
                    na = np.array(ja)
                    self.assertIs(dtype, na.dtype.type)
                    self.assertEqual(ja, na)
