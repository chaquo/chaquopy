import unittest


class TestPysha3(unittest.TestCase):

    def test_basic(self):
        import sha3
        k = sha3.keccak_512()
        k.update(b"data")
        self.assertEqual("1065aceeded3a5e4412e2187e919bffeadf815f5bd73d37fe00d384fe29f55f08462fdabe1007b993ce5b8119630e7db93101d9425d6e352e22ffe3dcb56b825",  # noqa: E501
                         k.hexdigest())
