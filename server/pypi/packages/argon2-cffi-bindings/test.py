import unittest


class TestArgon2Cffi(unittest.TestCase):

    # See https://argon2-cffi.readthedocs.io/en/stable/
    def test_basic(self):
        import argon2

        ph = argon2.PasswordHasher()
        hash = ph.hash("s3kr3tp4ssw0rd")
        self.assertTrue(hash.startswith("$argon2"), hash)
        self.assertTrue(ph.verify(hash, "s3kr3tp4ssw0rd"))
        with self.assertRaises(argon2.exceptions.VerifyMismatchError):
            ph.verify(hash, "s3kr3tp4sswOrd")
