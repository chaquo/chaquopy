import unittest


class TestKiwisolver(unittest.TestCase):

    # From https://kiwisolver.readthedocs.io/en/latest/basis/basic_systems.html
    def test_basic(self):
        from kiwisolver import Solver, Variable

        x1 = Variable('x1')
        x2 = Variable('x2')
        xm = Variable('xm')

        constraints = [x1 >= 0, x2 <= 100, x2 >= x1 + 10, xm == (x1 + x2) / 2]
        solver = Solver()
        for cn in constraints:
            solver.addConstraint(cn)

        solver.addConstraint((x1 == 40) | "weak")
        solver.addEditVariable(xm, 'strong')
        solver.suggestValue(xm, 60)
        solver.updateVariables()
        self.assertEqual(60, xm.value())
        self.assertEqual(40, x1.value())
        self.assertEqual(80, x2.value())
