import unittest


class TestPythonExample(unittest.TestCase):

    def test_basic(self):
        import python_example
        self.assertEqual(4, python_example.add(2, 2))
        with self.assertRaisesRegexp(TypeError, "incompatible function arguments"):
            python_example.add("one", "two")

        self.assertEqual(1, python_example.subtract(3, 2))
        self.assertEqual(-1, python_example.subtract(2, 3))
