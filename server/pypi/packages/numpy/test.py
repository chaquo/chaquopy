from __future__ import absolute_import, division, print_function

import unittest


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
