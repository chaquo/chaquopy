# This module is used by chaquopy.test.test_import.


def test_relative(self):
    with self.assertRaisesRegexp((ValueError, ImportError), r"^[Aa]ttempted relative import "
                                 r"(with no known parent package|in non-package)$"):
        from . import whatever  # noqa: F401
