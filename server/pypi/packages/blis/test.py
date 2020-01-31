import unittest


class TestBlis(unittest.TestCase):

    def test_einsum(self):
        from blis.py import einsum
        import numpy as np

        a = np.array([[1., 2.],
                      [3., 4.]])
        b = np.array([[2., 3.],
                      [5., 7.]])
        np.testing.assert_equal(np.array([[12., 17.],
                                          [26., 37.]]),
                                einsum("ab,bc->ac", a, b))
