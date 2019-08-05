import unittest


class TestGreenlet(unittest.TestCase):

    # From https://greenlet.readthedocs.io/en/latest/#introduction
    def test_basic(self):
        from greenlet import greenlet

        l = []

        def test1():
            l.append(12)
            gr2.switch()
            l.append(34)

        def test2():
            l.append(56)
            gr1.switch()
            l.append(78)

        gr1 = greenlet(test1)
        gr2 = greenlet(test2)
        gr1.switch()
        self.assertEqual([12, 56, 34], l)
