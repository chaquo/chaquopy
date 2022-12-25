# Keep valid Python 2 syntax so we can produce an actionable error message.
from __future__ import absolute_import, division, print_function

import sys


def check_build_python():
    MIN_VERSION = (3, 7)
    if sys.version_info < MIN_VERSION:
        print("buildPython must be version {}.{} or later: this is version {}.{}.{}. See "
              "https://chaquo.com/chaquopy/doc/current/android.html#buildpython."
              .format(*(MIN_VERSION + sys.version_info[:3])),
              file=sys.stderr)
        sys.exit(1)


class CommandError(Exception):
    pass
