import unittest


class TestCmakeExample(unittest.TestCase):

    def test_basic(self):
        import cmake_example
        self.assertEqual(4, cmake_example.add(2, 2))
        with self.assertRaisesRegex(TypeError, "incompatible function arguments"):
            cmake_example.add("one", "two")

        self.assertEqual(1, cmake_example.subtract(3, 2))
        self.assertEqual(-1, cmake_example.subtract(2, 3))
