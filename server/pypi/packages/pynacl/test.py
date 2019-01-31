import unittest


class TestPyNaCl(unittest.TestCase):

    # From https://pynacl.readthedocs.io/en/stable/password_hashing/
    def test_pwhash(self):
        import nacl.pwhash
        hashed = (b'$7$C6..../....qv5tF9KG2WbuMeUOa0TCoqwLHQ8s0TjQdSagne'
                  b'9NvU0$3d218uChMvdvN6EwSvKHMASkZIG51XPIsZQDcktKyN7')
        correct = b'my password'
        wrong = b'My password'

        self.assertTrue(nacl.pwhash.verify(hashed, correct))
        with self.assertRaises(nacl.exceptions.InvalidkeyError):
            nacl.pwhash.verify(hashed, wrong)
