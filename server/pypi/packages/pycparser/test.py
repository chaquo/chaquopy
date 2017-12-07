from __future__ import absolute_import, division, print_function

import unittest


class TestPycparser(unittest.TestCase):

    def test_basic(self):
        from pycparser.c_parser import CParser
        p = CParser()
        ast = p.parse("int x;")
        decl = ast.ext[0]
        self.assertEqual("x", decl.name)
        self.assertEqual(1, decl.coord.line)
        self.assertEqual(5, decl.coord.column)
