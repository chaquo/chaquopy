import unittest


class TestSklearn(unittest.TestCase):

    # See https://commons.wikimedia.org/wiki/File:Iris_dataset_scatterplot.svg (first column
    # from left, third row from top).
    def test_svm(self):
        from numpy.testing import assert_array_equal
        from sklearn import datasets, svm
        iris = datasets.load_iris()
        clf = svm.SVC(kernel="linear")
        clf.fit(iris.data[:, (0, 2)],  # (sepal_length, petal_length)
                iris.target)
        assert_array_equal([2, 2, 1,
                            2, 1, 1,
                            0, 0, 0],
                           clf.predict([[4.5, 5.0], [6.0, 5.0], [8.0, 5.0],
                                        [4.5, 4.7], [6.0, 4.7], [8.0, 4.7],
                                        [4.5, 2.0], [6.0, 2.0], [8.0, 2.0]]))
