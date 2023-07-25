import unittest


class TestPyerfa(unittest.TestCase):

    # https://pyerfa.readthedocs.io/en/latest/quickstart.html#usage
    def test_basic(self):
        import erfa
        from numpy.testing import assert_allclose

        position, velocity = erfa.plan94(2460000, 0, 1)
        assert_allclose(position, [0.090837128 , -0.3904139186, -0.2179738913])
        assert_allclose(velocity, [0.0219234131, 0.0070544853, 0.0014961814])
