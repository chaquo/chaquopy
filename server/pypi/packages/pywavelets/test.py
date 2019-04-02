import unittest


class TestPyWavelets(unittest.TestCase):

    def test_basic(self):
        import pywt
        cA, cD = pywt.dwt([1, 2, 3, 4], 'db1')
        self.assertAlmostEqual(2.12132034, cA[0])
        self.assertAlmostEqual(4.94974747, cA[1])
        self.assertAlmostEqual(-0.70710678, cD[0])
        self.assertAlmostEqual(-0.70710678, cD[1])
