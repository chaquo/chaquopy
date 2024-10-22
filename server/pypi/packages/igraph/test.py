import unittest


class TestIgraph(unittest.TestCase):

    def testGraphCreation(self):
        from igraph import Graph
        g = Graph()
        self.assertTrue(isinstance(g, Graph))
        self.assertTrue(g.vcount() == 0 and g.ecount() == 0 and not g.is_directed())

        g = Graph(3, [(0, 1), (1, 2), (2, 0)])
        self.assertTrue(
            g.vcount() == 3
            and g.ecount() == 3
            and not g.is_directed()
            and g.is_simple()
        )

        g = Graph(2, [(0, 1), (1, 2), (2, 3)], True)
        self.assertTrue(
            g.vcount() == 4 and g.ecount() == 3 and g.is_directed() and g.is_simple()
        )

        g = Graph([(0, 1), (1, 2), (2, 1)])
        self.assertTrue(
            g.vcount() == 3
            and g.ecount() == 3
            and not g.is_directed()
            and not g.is_simple()
        )

        g = Graph(((0, 1), (0, 0), (1, 2)))
        self.assertTrue(
            g.vcount() == 3
            and g.ecount() == 3
            and not g.is_directed()
            and not g.is_simple()
        )

        g = Graph(8, None)
        self.assertEqual(8, g.vcount())
        self.assertEqual(0, g.ecount())
        self.assertFalse(g.is_directed())

        g = Graph(edges=None)
        self.assertEqual(0, g.vcount())
        self.assertEqual(0, g.ecount())
        self.assertFalse(g.is_directed())

        self.assertRaises(TypeError, Graph, edgelist=[(1, 2)])