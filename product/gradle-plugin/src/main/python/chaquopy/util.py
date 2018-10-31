from __future__ import absolute_import, division, print_function

import sys


def check_build_python():
    if sys.version_info < (3, 4):
        print("buildPython must be version 3.4 or later: this is version {}.{}.{}. See "
              "https://chaquo.com/chaquopy/doc/current/android.html#buildpython."
              .format(*sys.version_info[:3]), file=sys.stderr)
        sys.exit(1)


class CommandError(Exception):
    pass
