#!/usr/bin/env python3
#
# Filter compiler command line to work around various issues.
#
# Usage: compiler-wrapper.py <path-to-compiler> <args...>

import os
from os.path import abspath, commonpath, dirname
import shlex
import sys


# Remove include and library directories which are not in known safe locations, such as
# the source directory, the host environment and the build environment.
valid_dirs = [abspath(f"{dirname(sys.argv[0])}/../..")]

def is_valid(dir):
    absdir = abspath(dir)
    return (
        any(commonpath([vd, absdir]) == vd for vd in valid_dirs)
        or (".cargo" in absdir) or (".rustup" in absdir)
    )


def main():
    args_in = sys.argv[1:]
    args_out = []
    args_removed = []

    def extend_if(valid, args):
        (args_out if valid else args_removed).extend(args)

    i = 0
    while i < len(args_in):
        arg = args_in[i]
        for prefix in ["-I", "-L"]:
            if arg.startswith(prefix):
                if arg == prefix:  # e.g. `-I path`
                    i += 1
                    dir = args_in[i]
                    extend_if(is_valid(dir), [arg, dir])
                else:  # e.g. `-Ipath`
                    extend_if(is_valid(arg[2:]), [arg])
                break
        else:
            # Debugging information will be stripped by build-wheel anyway, and in some
            # cases (e.g. lxml) can cause the compiler to use excessive memory.
            extend_if(arg != "-g", [arg])

        i += 1

    if args_removed:
        print(
            "Chaquopy: removed arguments: " + shlex.join(args_removed),
            file=sys.stderr)  # Some build systems hide the compiler's stdout.

    os.execv(args_out[0], args_out)


if __name__ == "__main__":
    main()
