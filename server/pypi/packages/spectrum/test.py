import unittest


class TestSpectrum(unittest.TestCase):

    # See https://pyspectrum.readthedocs.io/en/latest/tutorial_psd.html
    def test_psd(self):
        import numpy as np
        from spectrum import data_cosine, pminvar

        np.random.seed(999)
        p = pminvar(data_cosine(), 15)
        for i, expected in [(150, -28.4), (190, -17.2), (199, -4.2), (200, -3.0),
                            (201, -3.8), (210, -16.9), (250, -27.7)]:
            with self.subTest(i=i):
                self.assertAlmostEqual(expected, np.log10(p.psd[i]) * 10, places=1)

    # See https://pyspectrum.readthedocs.io/en/latest/ref_mtm.html. This test will fail if the
    # "mydpss" library cannot be loaded.
    def test_mtm(self):
        from numpy.testing import assert_allclose
        from spectrum import dpss

        w, _ = dpss(512, 2.5, 4)
        assert_allclose(w[150], [0.04145961, 0.06699996, 0.04388911, -0.01518164], rtol=1e-6)
