import unittest
import os
from importlib import metadata
from unittest import skipIf

scipy_version_info = tuple(map(int, metadata.version("scipy").split(".")))
os.environ["USE_PROPACK"] = "1"


class TestScipy(unittest.TestCase):

    def test_interpolate(self):
        import numpy as np
        from scipy.interpolate import griddata
        points = [[0, 0], [1, 0], [0, 1]]
        values = [1, 2, 3]
        np.testing.assert_allclose(
            [1, 1.5, 2, 2.5, 3],
            griddata(points, values, [[0, 0], [0.5, 0], [1, 0], [0.5, 0.5], [0, 1]]))
        np.testing.assert_allclose(
            [1.3, 1.7, 2.1, 2.5, np.nan],
            griddata(
                points,
                values,
                [[0.3, 0], [0.3, 0.2], [0.3, 0.4], [0.3, 0.6], [0.3, 0.8]]),
            equal_nan=True)

    def test_optimize(self):
        from scipy.optimize import minimize
        def f(x):
            return (x - 42) ** 2
        self.assertEqual(42, round(minimize(f, [123]).x[0]))

    @skipIf(scipy_version_info < (1, 8), "SciPy version too old")
    def test_csr_array(self):
        import numpy as np
        from scipy.sparse import csr_array
        indptr = np.array([0, 2, 3, 6])
        indices = np.array([0, 2, 2, 0, 1, 2])
        data = np.array([1, 2, 3, 4, 5, 6])
        np.testing.assert_array_equal(
            csr_array((data, indices, indptr), shape=(3, 3)).toarray(),
            [[1, 0, 2], [0, 0, 3], [4, 5, 6]])

    @skipIf(scipy_version_info < (1, 8), "SciPy version too old")
    def test_svds_propack(self):
        import numpy as np

        from scipy.stats import ortho_group
        from scipy.sparse import csc_matrix, diags
        from scipy.sparse.linalg import svds
        rng = np.random.default_rng()
        orthogonal = csc_matrix(ortho_group.rvs(10, random_state=rng))
        s = [0.0001, 0.001, 3, 4, 5]  # singular values
        u = orthogonal[:, :5]         # left singular vectors
        vT = orthogonal[:, 5:].T      # right singular vectors
        A = u @ diags(s) @ vT

        u2, s2, vT2 = svds(A, k=3, solver='propack')
        A2 = u2 @ np.diag(s2) @ vT2
        np.testing.assert_allclose(A2, A.todense(), atol=1e-3)

        u3, s3, vT3 = svds(A, k=5, solver='propack')
        A3 = u3 @ np.diag(s3) @ vT3
        np.testing.assert_allclose(A3, A.todense())

        np.testing.assert_allclose(s3, s)
        np.testing.assert_allclose(np.abs(u3), np.abs(u.toarray()))
        np.testing.assert_allclose(np.abs(vT3), np.abs(vT.toarray()))
