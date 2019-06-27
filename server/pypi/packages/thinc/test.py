import unittest


class TestThinc(unittest.TestCase):

    # Thinc is "the machine learning library powering spaCy", and apparently has no public API
    # of its own.
    def test_basic(self):
        import thinc  # noqa: F401
