import unittest


class TestRawpy(unittest.TestCase):

    def test_basic(self):
        from io import BytesIO
        import rawpy

        URL = "https://www.rawsamples.ch/raws/nikon/RAW_NIKON_D5000.NEF"
        with BytesIO(read_url(URL)) as f, rawpy.imread(f) as raw:
            self.assertEqual(b"RGBG", raw.color_desc)
            self.assertEqual(4310, raw.sizes.width)
            self.assertEqual(2868, raw.sizes.height)


# Downloading a URL with "Connection: close", as urllib does, causes an intermittent
# network problem on the emulator (https://issuetracker.google.com/issues/150758736). For
# small files we could just retry until it succeeds, but for large files a failure is much more
# likely, and we might have to keep retrying for several minutes. So use the stdlib's low-level
# HTTP API to make a request with no Connection header.
def read_url(url):
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import urlparse

    parsed = urlparse(url)
    conn_cls = HTTPSConnection if parsed.scheme == "https" else HTTPConnection
    conn = conn_cls(parsed.hostname, parsed.port)
    full_path = parsed.path
    if parsed.query:
        full_path += "?" + parsed.query
    conn.request("GET", full_path)
    resp = conn.getresponse()
    assert resp.status == 200, resp.status
    data = resp.read()
    conn.close()
    return data
