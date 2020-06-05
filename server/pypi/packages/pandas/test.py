import unittest

try:
    from android.os import Build
except ImportError:
    Build = None


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

    @unittest.skipUnless(Build, "Android only")
    def test_jarray(self):
        from java import jarray, jshort
        from pandas import DataFrame

        ja = jarray(jshort)([-10000, 0, 10000])
        df_col = DataFrame(ja)
        self.assertEqual((len(ja), 1), df_col.shape)
        self.assertEqual(ja, df_col[0].tolist())

        df_cols = DataFrame({"a": ja, "b": ja})
        self.assertEqual((len(ja), 2), df_cols.shape)
        self.assertEqual(ja, df_cols["a"])
        self.assertEqual(ja, df_cols["b"])

        df_rows = DataFrame([ja, ja])
        self.assertEqual((2, len(ja)), df_rows.shape)
        self.assertEqual(ja, df_rows.loc[0])
        self.assertEqual(ja, df_rows.loc[1])
