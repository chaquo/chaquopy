import unittest

class TestTiktoken(unittest.TestCase):

    def test_encode_decode(self):
        import tiktoken
        enc = tiktoken.get_encoding("gpt2")
        text = "hello world"
        tokens = enc.encode(text)
        print("Encoded tokens:", tokens)
        decoded = enc.decode(tokens)
        print("Decoded text:", decoded)
        self.assertEqual(decoded, text)

    def test_empty_string(self):
        import tiktoken
        enc = tiktoken.get_encoding("gpt2")
        tokens = enc.encode("")
        print("Encoded tokens for empty string:", tokens)
        decoded = enc.decode(tokens)
        print("Decoded text for empty string:", decoded)
        self.assertEqual(decoded, "")

    def test_token_count(self):
        import tiktoken
        enc = tiktoken.get_encoding("gpt2")
        text = "OpenAI rocks!"
        tokens = enc.encode(text)
        print("Token count:", len(tokens), "Tokens:", tokens)
        self.assertTrue(len(tokens) > 0)
        self.assertIsInstance(tokens, list)

if __name__ == "__main__":
    unittest.main()