import unittest


class TestPycurl(unittest.TestCase):

    # See http://pycurl.io/docs/latest/quickstart.html
    def test_basic(self):
        import certifi
        import io
        import pycurl

        buffer = io.BytesIO()
        c = pycurl.Curl()
        c.setopt(c.URL, 'https://google.com/')
        c.setopt(c.WRITEDATA, buffer)
        c.setopt(c.CAINFO, certifi.where())
        c.setopt(c.FOLLOWLOCATION, True)
        c.perform()
        c.close()
        body = buffer.getvalue()

        doctype = b"<!doctype html>"
        self.assertEqual(doctype, body[:len(doctype)].lower(), body)
