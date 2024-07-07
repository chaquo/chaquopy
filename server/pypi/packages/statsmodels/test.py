import unittest


class TestStatsmodels(unittest.TestCase):

    # See https://en.wikipedia.org/wiki/Anscombe%27s_quartet
    def test_anscombe(self):
        import ssl
        import statsmodels.api as sm
        import statsmodels.formula.api as smf

        # See https://issuetracker.google.com/issues/150758736. Although the dataset
        # itself is small, it also needs to download a 300K dataset index file, which
        # sometimes takes over 100 retries on the API 28 emulator.
        retries = 0
        while True:
            try:
                data = sm.datasets.get_rdataset("anscombe").data
                if retries:
                    print(f"Downloaded dataset after {retries} retries")
                break
            except ssl.SSLError:
                print(".", end="")
                retries += 1

        for i in range(1, 5):
            with self.subTest(i=i):
                results = smf.ols(formula=f"y{i} ~ x{i}", data=data).fit()
                self.assertAlmostEqual(3, round(results.params["Intercept"], 2))
                self.assertAlmostEqual(0.5, round(results.params[f"x{i}"], 3))
                self.assertAlmostEqual(0.67, round(results.rsquared, 2))
