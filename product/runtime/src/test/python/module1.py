# This module is used by test_import and test_android.


def test_relative(self):
    with self.assertRaisesRegex((ValueError, ImportError), r"^[Aa]ttempted relative import "
                                r"(with no known parent package|in non-package)$"):
        from . import whatever  # noqa: F401
