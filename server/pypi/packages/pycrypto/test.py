import unittest


class TestPycrypto(unittest.TestCase):

    def test_aes(self):
        from Crypto.Cipher import AES

        plaintext = b"hello world     "  # Padded to 16 bytes
        key = b'\x94\xed\x84d\x8e\xf4\n\xf9\x85\xdc\xefC>\x90Y.'

        ciphertext = AES.new(key, AES.MODE_ECB).encrypt(plaintext)
        self.assertEqual(b'\xb7H\xd3\x8e\xb2\xfe\xfc?\x133\xa1\x9b?\xda>}', ciphertext)
        self.assertEqual(plaintext, AES.new(key, AES.MODE_ECB).decrypt(ciphertext))
