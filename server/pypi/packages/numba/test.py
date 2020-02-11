import unittest


class TestNumba(unittest.TestCase):

    def test_basic(self):
        import numba

        @numba.jit
        def add(a, b):
            return a + b

        self.assertIsInstance(add, numba.dispatcher.Dispatcher)
        self.assertEqual(9, add(2, 7))
        self.assertEqual(4.5, add(1.0, 3.5))
