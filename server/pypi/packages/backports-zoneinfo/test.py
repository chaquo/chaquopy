import unittest


class TestBackportsZoneinfo(unittest.TestCase):

    # Based on https://docs.python.org/3/library/zoneinfo.html
    def test_basic(self):
        from backports.zoneinfo import ZoneInfo
        from datetime import datetime

        dt = datetime(2020, 10, 31, 12, tzinfo=ZoneInfo("America/Los_Angeles"))
        self.assertEqual("2020-10-31 12:00:00-07:00", str(dt))
        self.assertEqual("PDT", dt.tzname())
