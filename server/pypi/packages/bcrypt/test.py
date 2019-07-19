import unittest


class TestBcrypt(unittest.TestCase):

    def test_basic(self):
        import bcrypt
        hashed = b"$2b$12$9cwzD/MRnVT7uvkxAQvkIejrif4bwRTGvIRqO7xf4OYtDQ3sl8CWW"
        self.assertTrue(bcrypt.checkpw(b"password", hashed))
        self.assertFalse(bcrypt.checkpw(b"passwerd", hashed))
