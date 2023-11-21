# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
from __future__ import absolute_import, division, print_function

__all__ = [
    "__title__",
    "__summary__",
    "__uri__",
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__copyright__",
]

__title__ = "packaging"
__summary__ = "Core utilities for Python packages"
__uri__ = "https://github.com/pypa/packaging"

# Chaquopy: backported from pip 21.0.1 to get support for newer macOS wheel tags: arm64,
# universal2, and version numbers 11 and higher. See test_wheel_index and
# test_download_sdist.
__version__ = "20.9"

__author__ = "Donald Stufft and individual contributors"
__email__ = "donald@stufft.io"

__license__ = "BSD-2-Clause or Apache-2.0"
__copyright__ = "2014-2019 %s" % __author__
