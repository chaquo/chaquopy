import unittest


class TestEditdistance(unittest.TestCase):

    def test_basic(self):
        import editdistance
        self.assertEqual(3, editdistance.eval("banana", "bahamas"))
