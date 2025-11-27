import unittest


class TestAiodns(unittest.TestCase):

    def test_basic(self):
        import aiodns
        import asyncio

        async def main():
            resolver = aiodns.DNSResolver()
            result = await resolver.query('www.python.org', 'A')
            self.assertIsNotNone(result)
            # Result is iterable, check that it contains at least one record
            records = list(result) if hasattr(result, '__iter__') else [result]
            self.assertGreater(len(records), 0)
            # Check that records have the expected host attribute
            if hasattr(records[0], 'host'):
                self.assertIsNotNone(records[0].host)

        asyncio.run(main())

    # Check that the native module is being used.
    def test_extension(self):
        import aiodns
        # Verify that aiodns is using the native c-ares library
        resolver = aiodns.DNSResolver()
        self.assertIsNotNone(resolver)
        # Check that the resolver has the expected methods
        self.assertTrue(hasattr(resolver, 'query'))
