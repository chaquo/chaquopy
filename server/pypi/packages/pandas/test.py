from __future__ import absolute_import, division, print_function

import unittest


class TestPandas(unittest.TestCase):

    def test_basic(self):
        from pandas import DataFrame
        df = DataFrame([("alpha", 1), ("bravo", 2), ("charlie", 3)],
                       columns=["Letter", "Number"])
        self.assertEqual(",Letter,Number\n"
                         "0,alpha,1\n"
                         "1,bravo,2\n"
                         "2,charlie,3\n",
                         df.to_csv())
