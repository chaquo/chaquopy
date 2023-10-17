import unittest

class TestLap(unittest.TestCase):

    def test_lapmod(self):
        import numpy as np
        from lap import lapjv, lapmod
        from .test_utils import (
            get_dense_8x8_int,
            get_dense_100x100_int, get_dense_100x100_int_hard, get_sparse_100x100_int,
            get_dense_1kx1k_int, get_dense_1kx1k_int_hard, get_sparse_1kx1k_int,
            get_sparse_4kx4k_int,
            get_dense_eps,
            get_platform_maxint,
            sparse_from_dense, sparse_from_masked
        )

        #test_square
        ret = lapmod(*sparse_from_dense(cost))
        self.assertEqual(len(ret), len(expected))
        self.assertEqual(cost[range(cost.shape[0]), ret[1]].sum(), ret[0])
        self.assertEqual(cost[ret[2], range(cost.shape[1])].sum(), ret[0])
        self.assertEqual(ret[0], expected[0])
        self.assertEqual(np.all(ret[1], expected[1]), True)
        self.assertEqual(np.all(ret[2], expected[2]), True)
        dense_ret = lapjv(cost)
        self.assertEqual(ret[0], dense_ret[0])
        self.assertEqual(np.all(ret[1], dense_ret[1]), True)
        self.assertEqual(np.all(ret[2], dense_ret[2]), True)

        #test_sparse_square
        ret = lapmod(*sparse_from_masked(cost))
        self.assertEqual(len(ret), len(expected))
        self.assertEqual(cost[range(cost.shape[0]), ret[1]].sum(), ret[0])
        self.assertEqual(cost[ret[2], range(cost.shape[1])].sum(), ret[0])
        self.assertEqual(ret[0], expected[0])
        self.assertEqual(np.all(ret[1] == expected[1]), True)
        self.assertEqual(np.all(ret[2] == expected[2]), True)
        dense_ret = lapjv(cost)
        self.assertEqual(ret[0], dense_ret[0])
        self.assertEqual(np.all(ret[1] == dense_ret[1]), True)
        self.assertEqual(np.all(ret[2] == dense_ret[2]), True)

    def test_lapjv(self):
        import numpy as np
        from lap import lapjv
        from .test_utils import (
            get_dense_8x8_int,
            get_dense_100x100_int, get_dense_100x100_int_hard, get_sparse_100x100_int,
            get_dense_1kx1k_int, get_dense_1kx1k_int_hard, get_sparse_1kx1k_int,
            get_sparse_4kx4k_int,
            get_dense_eps,
            get_platform_maxint
        )

        #test_inf_unique
        cost = np.array([[1000, 4, 1],
                     [1, 1000, 3],
                     [5, 1, 1000]])
        cost_ext = np.empty((4, 4))
        cost_ext[:] = np.inf
        cost_ext[:3, :3] = cost
        cost_ext[3, 3] = 0
        ret = lapjv(cost_ext)
        self.assertEqual(len(ret), 3)
        self.assertEqual(ret[0], 3.)
        self.assertEqual(np.all(ret[1] == [2, 0, 1, 3]), True)

        #test_all_inf
        cost = np.empty((5, 5), dtype=float)
        cost[:] = np.inf
        ret = lapjv(cost)
        self.assertEqual(len(ret), 3)
        self.assertEqual(ret[0], np.inf)

    def test_arr_loop(self):
        import numpy as np
        from lap import lapjv

        #test_lapjv_arr_loop
        shape = (7, 3)
        cc = np.array([
            2.593883482138951146e-01, 3.080381437461217620e-01,
            1.976243020727339317e-01, 2.462740976049606068e-01,
            4.203993396282833528e-01, 4.286184525458427985e-01,
            1.706431415909629434e-01, 2.192929371231896185e-01,
            2.117769622802734286e-01, 2.604267578125001315e-01])
        ii = np.array([0, 0, 1, 1, 2, 2, 5, 5, 6, 6])
        jj = np.array([0, 1, 0, 1, 1, 2, 0, 1, 0, 1])
        cost = np.empty(shape)
        cost[:] = 1000.
        cost[ii, jj] = cc
        opt, ind1, ind0 = lapjv(cost, extend_cost=True, return_cost=True)
        self.assertEqual(opt, approx(0.8455356917416, 1e-10))
        self.assertEqual(np.all(ind0 == [5, 1, 2]) or np.all(ind0 == [1, 5, 2]), True)
