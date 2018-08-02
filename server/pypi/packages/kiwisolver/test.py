from __future__ import absolute_import, division, print_function

import unittest


class TestKiwisolver(unittest.TestCase):

    # Minimal import test: we only added this package because it's a dependency of matplotlib.
    def test_basic(self):
        import kiwisolver  # noqa: F401
