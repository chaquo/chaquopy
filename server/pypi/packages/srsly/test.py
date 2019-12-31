import unittest


class TestSrsly(unittest.TestCase):

    def test_basic(self):
        import srsly
        data = {"foo": "bar", "baz": 123}
        self.assertEqual('{"foo":"bar","baz":123}', srsly.json_dumps(data))
        self.assertEqual('{"baz":123,"foo":"bar"}',
                         srsly.json_dumps(data, sort_keys=True))
