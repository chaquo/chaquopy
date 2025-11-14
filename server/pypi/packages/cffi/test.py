import unittest


class TestCffi(unittest.TestCase):

    def test_basic(self):
        from cffi import FFI
        ffi = FFI()
        ffi.cdef("size_t strlen(char *str);")
        lib = ffi.dlopen(None)
        self.assertEqual(11, lib.strlen(ffi.new("char[]", b"hello world")))
