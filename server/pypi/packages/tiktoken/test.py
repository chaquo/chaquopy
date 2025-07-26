import unittest

class TestTiktoken(unittest.TestCase):

    def test_encode_decode(self):
        import tiktoken
        enc = tiktoken.get_encoding("gpt2")
        text = "hello world"
        tokens = enc.encode(text)
        self.assertIsInstance(tokens, list)
        self.assertEqual(len(tokens), 2, tokens)
        decoded = enc.decode(tokens)
        self.assertEqual(decoded, text)

    def test_empty_string(self):
        import tiktoken
        enc = tiktoken.get_encoding("gpt2")
        tokens = enc.encode("")
        self.assertIsInstance(tokens, list)
        self.assertEqual(len(tokens), 0, tokens)
        decoded = enc.decode(tokens)
        self.assertEqual(decoded, "")
