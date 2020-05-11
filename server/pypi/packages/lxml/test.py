import unittest


class TestLxml(unittest.TestCase):

    def test_basic(self):
        from lxml import etree
        parent = etree.fromstring("<parent><child name='one'/><child name='two'/></parent>")
        self.assertEqual("parent", parent.tag)
        self.assertEqual(2, len(parent))
        self.assertEqual("one", parent[0].get("name"))
        self.assertEqual("two", parent[1].get("name"))
