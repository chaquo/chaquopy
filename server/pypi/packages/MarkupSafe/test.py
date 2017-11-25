import unittest

class TestMarkupSafe(unittest.TestCase):

    def test_basic(self):
        from markupsafe import escape
        self.assertEqual("&lt;script&gt;", escape("<script>"))
