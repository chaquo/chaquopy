import unittest


class TestMultidict(unittest.TestCase):

    def test_basic(self):
        from multidict import MultiDict
        md = MultiDict()
        md.add("key", "value2")
        md.add("key", "value1")
        self.assertEqual("value2", md["key"])
        self.assertEqual(["value2", "value1"], md.getall("key"))
