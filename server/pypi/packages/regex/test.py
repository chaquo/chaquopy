import unittest


class TestRegex(unittest.TestCase):

    def test_basic(self):
        import regex
        self.assertEquals("cde", regex.search(r"(\w\w\K\w\w\w)", "abcdef")[0])
