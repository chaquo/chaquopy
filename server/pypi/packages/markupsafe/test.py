from __future__ import absolute_import, division, print_function

import unittest


class TestMarkupSafe(unittest.TestCase):

    def test_basic(self):
        from markupsafe import escape
        self.assertEqual("&lt;script&gt;", escape("<script>"))
