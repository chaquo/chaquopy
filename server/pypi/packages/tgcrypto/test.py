import os
import unittest


class TestTgCrypto(unittest.TestCase):

    # See https://github.com/pyrogram/tgcrypto/blob/v1.2.5/README.md
    def test_basic(self):
        import tgcrypto

        data = os.urandom(10 * 1024)
        key = os.urandom(32)
        iv = os.urandom(32)

        ige_encrypted = tgcrypto.ige256_encrypt(data, key, iv)
        self.assertNotEqual(ige_encrypted, data)
        ige_decrypted = tgcrypto.ige256_decrypt(ige_encrypted, key, iv)
        self.assertEqual(ige_decrypted, data)
