import unittest


class TestMarisaTrie(unittest.TestCase):

    # https://marisa-trie.readthedocs.io/en/latest/tutorial.html
    def test_basic(self):
        import marisa_trie

        t = marisa_trie.Trie(["key1", "key2", "key12"])
        self.assertIn("key1", t)
        self.assertNotIn("key20", t)
        self.assertEqual(t.keys("key1"), ["key1", "key12"])
