import unittest


class TestTypedAst(unittest.TestCase):

    # Test parsing something which is valid in Python 2 but not in Python 3.
    def test_ast27(self):
        from typed_ast import ast27
        mod_node = ast27.parse("print 'Hello world'")
        self.assertIsInstance(mod_node, ast27.Module)
        print_node = mod_node.body[0]
        self.assertIsInstance(print_node, ast27.Print)
        str_node = print_node.values[0]
        self.assertIsInstance(str_node, ast27.Str)
        self.assertEqual(b"Hello world", str_node.s)
