import unittest


class TestTornado(unittest.TestCase):

    def test_mask(self):
        # This function is the only compiled component. Tests taken from
        # https://github.com/tornadoweb/tornado/blob/master/tornado/test/websocket_test.py.
        from tornado.speedups import websocket_mask
        self.assertEqual(websocket_mask(b"ZXCV", b"98765432"), b"c`t`olpd")
