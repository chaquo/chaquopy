import unittest


class TestCasadi(unittest.TestCase):

    def test_basic(self):
        from casadi import jacobian, sin, SX
        a = SX.sym("a")
        self.assertEqual("cos(a)", str(jacobian(sin(a), a)))
