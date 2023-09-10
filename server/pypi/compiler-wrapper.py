#!/usr/bin/env python3
#
# Filter compiler command line to remove include and library directories which are not
# in known safe locations.

import os
from os.path import abspath, commonpath, dirname
import sys


# This covers the source directory, the host environment and the build environment.
valid_dirs = [abspath(f"{dirname(sys.argv[0])}/../..")]

def is_valid(dir, prefix):
    if any(commonpath([vd, abspath(dir)]) == vd for vd in valid_dirs):
        return True
    else:
        print(f"Chaquopy: ignored invalid {prefix} directory: {dir!r}", file=sys.stderr)
        return False


def main():
    args_in = sys.argv[1:]
    args_out = []

    i = 0
    while i < len(args_in):
        arg = args_in[i]
        for prefix in ["-I", "-L"]:
            if arg.startswith(prefix):
                if arg == prefix:
                    i += 1
                    dir = args_in[i]
                    if is_valid(dir, prefix):
                        args_out += [arg, dir]
                else:
                    dir = arg[2:]
                    if is_valid(dir, prefix):
                        args_out.append(arg)
                break
        else:
            args_out.append(arg)

        i += 1

    os.execv(args_out[0], args_out)


if __name__ == "__main__":
    main()
