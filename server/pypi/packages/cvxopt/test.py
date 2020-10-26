import unittest

class TestCvxopt(unittest.TestCase):

    # See https://cvxopt.org/userguide/spsolvers.html#cvxopt.cholmod.linsolve
    def test_cholmod(self):
        from cvxopt import matrix, spmatrix, cholmod
        A = spmatrix([10, 3, 5, -2, 5, 2], [0, 2, 1, 3, 2, 3], [0, 0, 1, 1, 2, 3])
        X = matrix(range(8), (4, 2), 'd')
        cholmod.linsolve(A, X)
        self.assertEqual("[-1.46e-01  4.88e-02]\n"
                         "[ 1.33e+00  4.00e+00]\n"
                         "[ 4.88e-01  1.17e+00]\n"
                         "[ 2.83e+00  7.50e+00]\n",
                         str(X))

    # See https://github.com/neuropsychology/NeuroKit/blob/master/tests/tests_eda.py
    def test_eda_phasic(self):
        import neurokit2 as nk

        sampling_rate = 1000
        eda = nk.eda_simulate(duration=30, sampling_rate=sampling_rate, scr_number=6,
                              noise=0.01, drift=0.01, random_state=42)
        cvxEDA = nk.eda_phasic(nk.standardize(eda), method="cvxeda")
        assert len(cvxEDA) == len(eda)
        print(cvxEDA)  # See meta.yaml for expected output.
