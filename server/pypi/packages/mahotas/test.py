import unittest

class TestMahotas(unittest.TestCase):

    def test_hitmiss(self):
        import mahotas
        import numpy as np

        A = np.zeros((100,100), np.bool_)
        Bc = np.array([
            [0,1,2],
            [0,1,1],
            [2,1,1]])
        mahotas.morph.hitmiss(A,Bc)
        self.assertFalse(mahotas.morph.hitmiss(A,Bc).sum())

        A[4:7,4:7] = np.array([
            [0,1,1],
            [0,1,1],
            [0,1,1]])
        self.assertEqual(mahotas.morph.hitmiss(A,Bc).sum(), 1)
        self.assertTrue(mahotas.morph.hitmiss(A,Bc)[5,5])
