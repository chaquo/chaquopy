import unittest

class TestDepthAI(unittest.TestCase):
    def test_import(self):
        try:
            import depthai  # noqa: F401
        except ImportError:
            print("Unable to import DepthAI module!")
            raise
