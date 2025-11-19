import unittest


class TestMarkupSafe(unittest.TestCase):

    def test_basic(self):
        # Explicitly check this module can be imported, otherwise it'll silently use a
        # pure-Python implementation.
        from markupsafe import _speedups  # noqa: F401

        from markupsafe import escape
        self.assertEqual("&lt;script&gt;", escape("<script>"))
