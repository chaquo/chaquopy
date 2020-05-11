import unittest

try:
    from android.os import Build  # noqa: F401
    is_android = True
except ImportError:
    is_android = False

class TestCffi(unittest.TestCase):

    def test_basic(self):
        from cffi import FFI
        ffi = FFI()
        ffi.cdef("size_t strlen(char *str);")
        lib = ffi.dlopen("libc.so" if is_android else None)  # `None` doesn't work on API 15.
        self.assertEqual(11, lib.strlen(ffi.new("char[]", b"hello world")))
