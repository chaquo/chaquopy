import unittest


class TestAstropy(unittest.TestCase):

    # https://docs.astropy.org/en/stable/convolution/index.html#getting-started
    def test_convolution(self):
        from astropy.convolution import convolve
        from numpy.testing import assert_allclose

        assert_allclose(convolve([1, 4, 5, 6, 5, 7, 8], [0.2, 0.6, 0.2]),
                        [1.4, 3.6, 5.0, 5.6, 5.6, 6.8, 6.2])
