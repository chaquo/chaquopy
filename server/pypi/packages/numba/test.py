import unittest


class TestNumba(unittest.TestCase):

    def test_basic(self):
        import numba
        import os
        from os.path import dirname, exists
        import shutil
        import sys
        import traceback

        cache_dir = f"{dirname(__file__)}/__pycache__"
        if exists(cache_dir):
            shutil.rmtree(cache_dir)

        ref_line_no = traceback.extract_stack()[-1][1]  # Line number of THIS line.
        @numba.jit(cache=True)
        def add(a, b):
            return a + b

        self.assertIsInstance(add, numba.dispatcher.Dispatcher)
        self.assertEqual(9, add(2, 7))
        self.assertEqual(4.5, add(1.0, 3.5))

        self.assertTrue(exists(cache_dir))
        func_name = __name__.rpartition(".")[2] + ".TestNumba.test_basic.locals.add"
        py_tag = "py" + "".join(map(str, sys.version_info[:2]))
        self.assertIn(f"{func_name}-{ref_line_no + 1}.{py_tag}.nbi", os.listdir(cache_dir))
