import unittest

class TestBitarray(unittest.TestCase):

    # See https://github.com/ilanschnell/bitarray/blob/master/README.md
    def test_basic(self):
        from bitarray import bitarray

        a = bitarray()
        a.append(True)
        a.extend([False, True, True])
        self.assertEqual(bitarray("1011"), a)
        self.assertNotEqual(bitarray("1111"), a)

        b = bitarray("1100")
        self.assertEqual(bitarray("1000"), a & b)
        self.assertEqual(bitarray("1111"), a | b)
        self.assertEqual(bitarray("0111"), a ^ b)

        a[:] = True
        self.assertEqual(bitarray("1111"), a)
