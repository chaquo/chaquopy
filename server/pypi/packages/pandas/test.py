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

    # See notes at https://github.com/chaquo/chaquopy/issues/306
    @unittest.skipUnless(Build, "Android only")
    def test_jarray(self):
        from java import jarray, jshort
        from pandas import DataFrame
        from pandas.testing import assert_frame_equal

        ja = jarray(jshort)([-10000, 0, 10000])
        ja_2 = jarray(jshort)([-20000, 0, 20000])

        df_cols = DataFrame({"a": ja, "b": ja_2})
        self.assertEqual((3, 2), df_cols.shape)
        self.assertEqual(ja, df_cols["a"])
        self.assertEqual(ja_2, df_cols["b"])

        df_rows = DataFrame([ja, ja_2])
        self.assertEqual((2, 3), df_rows.shape)
        self.assertEqual(ja, df_rows.loc[0])
        self.assertEqual(ja_2, df_rows.loc[1])

        df_2d = DataFrame(jarray(jarray(jshort))([ja, ja_2]))
        assert_frame_equal(df_rows, df_2d)
