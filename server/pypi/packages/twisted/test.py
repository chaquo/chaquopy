from __future__ import absolute_import, division, print_function

import sys
import unittest


class TestTwisted(unittest.TestCase):

    def test_basic(self):
        # There's only one native module, and it's internal and Python 2-only, so an import
        # test is sufficient.
        from twisted.python import sendmsg
        is_py2 = sys.version_info[0] < 3
        self.assertEqual(is_py2, hasattr(sendmsg, "send1msg"))
        self.assertEqual(is_py2, "twisted.python._sendmsg" in sys.modules)
