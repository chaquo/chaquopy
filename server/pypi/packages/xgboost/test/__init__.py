import unittest


class TestXgboost(unittest.TestCase):

    # Based on https://github.com/dmlc/xgboost/blob/master/demo/guide-python/basic_walkthrough.py.
    def test_basic(self):
        from os.path import dirname, join
        from sklearn.datasets import load_svmlight_file
        import xgboost as xgb

        CURRENT_DIR = dirname(__file__)

        # X is a scipy csr matrix, XGBoost supports many other input types,
        X, y = load_svmlight_file(join(CURRENT_DIR, "agaricus.txt.train"))
        dtrain = xgb.DMatrix(X, y)
        # validation set
        X_test, y_test = load_svmlight_file(join(CURRENT_DIR, "agaricus.txt.test"))
        dtest = xgb.DMatrix(X_test, y_test)

        # specify parameters via map, definition are same as c++ version
        param = {'max_depth': 2, 'eta': 1, 'objective': 'binary:logistic'}

        # specify validations set to watch performance
        watchlist = [(dtest, 'eval'), (dtrain, 'train')]
        num_round = 2
        bst = xgb.train(param, dtrain, num_round, watchlist, verbose_eval=False)

        # this is prediction
        preds = bst.predict(dtest)
        labels = dtest.get_label()
        error = (sum(1 for i in range(len(preds)) if int(preds[i] > 0.5) != labels[i]) /
                 float(len(preds)))
        self.assertGreater(error, 0)
        self.assertLess(error, 0.1)
