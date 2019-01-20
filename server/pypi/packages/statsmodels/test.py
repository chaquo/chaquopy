import unittest


class TestStatsmodels(unittest.TestCase):

    # See https://en.wikipedia.org/wiki/Anscombe%27s_quartet
    def test_anscombe(self):
        import statsmodels.api as sm
        import statsmodels.formula.api as smf

        data = sm.datasets.get_rdataset("anscombe").data
        for i in range(1, 5):
            with self.subTest(i=i):
                results = smf.ols(formula=f"y{i} ~ x{i}", data=data).fit()
                self.assertAlmostEqual(3, round(results.params[f"Intercept"], 2))
                self.assertAlmostEqual(0.5, round(results.params[f"x{i}"], 3))
                self.assertAlmostEqual(0.67, round(results.rsquared, 2))
