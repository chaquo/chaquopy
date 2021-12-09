import unittest


class TestFrozenList(unittest.TestCase):

    def test_basic(self):
        from frozenlist import FrozenList

        fl = FrozenList([17, 42])
        fl.append("spam")
        self.assertEqual([17, 42, "spam"], fl)

        fl.freeze()
        with self.assertRaisesRegex(RuntimeError, "Cannot modify frozen list"):
            fl.append("Monty")
