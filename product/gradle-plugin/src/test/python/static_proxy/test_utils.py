from unittest import TestCase
from warnings import catch_warnings, filterwarnings


class FilterWarningsCase(TestCase):

    def setUp(self):
        super(FilterWarningsCase, self).setUp()
        self.cw = catch_warnings()
        self.cw.__enter__()
        filterwarnings("error")

    def tearDown(self):
        self.cw.__exit__(None, None, None)
        super(FilterWarningsCase, self).tearDown()
