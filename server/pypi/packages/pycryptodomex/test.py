import unittest


# pycryptodome and pycryptodomex are identical except for the name of their top-level package.
# Any change to one should also be done to the other.
class TestPycryptodomex(unittest.TestCase):

    def test_aes(self):
        from Cryptodome.Cipher import AES

        plaintext = b"hello world"
        key = b'\x94\xed\x84d\x8e\xf4\n\xf9\x85\xdc\xefC>\x90Y.'
        nonce = b'\xee\x15 W4\\%\xa2\xc6\xef\x05\xbb,\xbaB\xa3'

        ciphertext = AES.new(key, AES.MODE_EAX, nonce).encrypt(plaintext)
        self.assertEqual(b'\x83\xd8Z\xa0\xc2\xd4P\xc0\x00\x88\x08', ciphertext)
        self.assertEqual(plaintext, AES.new(key, AES.MODE_EAX, nonce).decrypt(ciphertext))
