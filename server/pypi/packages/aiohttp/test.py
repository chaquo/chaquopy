import unittest


class TestAiohttp(unittest.TestCase):

    def test_basic(self):
        import aiohttp
        import asyncio

        async def main():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://www.python.org/') as response:
                    self.assertEqual(200, response.status)
                    self.assertRegex(response.headers['content-type'], r"^text/html")

        asyncio.run(main())

    # Check that the native module is being used.
    def test_extension(self):
        from aiohttp import http_parser, _http_parser
        self.assertIs(http_parser.HttpResponseParser, _http_parser.HttpResponseParser)
        self.assertIsNot(http_parser.HttpResponseParser, http_parser.HttpResponseParserPy)
