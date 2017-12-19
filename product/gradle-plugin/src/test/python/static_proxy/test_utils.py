from __future__ import absolute_import, division, print_function

from unittest import TestCase
from warnings import catch_warnings, filterwarnings


class FilterWarningsCase(TestCase):

    def setUp(self):
        super(FilterWarningsCase, self).setUp()
        self.cw = catch_warnings()
        self.cw.__enter__()
        filterwarnings("error")
        filterwarnings("ignore", r"Please use assert\w+ instead")

    def tearDown(self):
        super(FilterWarningsCase, self).tearDown()
        self.cw.__exit__(None, None, None)
