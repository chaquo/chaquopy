# This module is used by chaquopy.test.test_import.


def test_relative(self):
    with self.assertRaisesRegexp(ValueError, (r"^[Aa]ttempted relative import (with no known "
                                              r"parent package)|(in non-package)$")):
        from . import whatever  # noqa: F401
