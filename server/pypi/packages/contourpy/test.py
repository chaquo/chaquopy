import unittest


class ContourPy(unittest.TestCase):

    # https://contourpy.readthedocs.io/en/v1.0.5/quickstart.html
    def test_basic(self):
        from contourpy import contour_generator
        from numpy.testing import assert_allclose

        z = [[0.0, 0.1], [0.2, 0.3]]
        cont_gen = contour_generator(z=z)
        assert_allclose(cont_gen.lines(0.25), [[[0.5, 1], [1, 0.75]]])
        assert_allclose(cont_gen.lines(0.2), [[[0, 1], [1, 0.5]]])
