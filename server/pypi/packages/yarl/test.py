import unittest


class TestYarl(unittest.TestCase):

    def test_basic(self):
        from yarl import URL
        self.assertEqual(
            "http://xn--jxagkqfkduily1i.eu/%D0%BF%D1%83%D1%82%D1%8C/%E9%80%99%E8%A3%A1",
            str(URL("http://εμπορικόσήμα.eu/путь/這裡")))
