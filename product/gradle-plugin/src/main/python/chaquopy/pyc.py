#!/usr/bin/env python3

"""Copyright (c) 2019 Chaquo Ltd. All rights reserved."""

# Keep valid Python 2 syntax so we can produce an error message.
from __future__ import absolute_import, division, print_function

# Do this as early as possible to minimize the chance of something else going wrong and causing
# a less comprehensible error message.
from .util import check_build_python
check_build_python()

import argparse
from compileall import compile_dir
import importlib.util
import os
from os.path import isfile, join
import sys


EXPECTED_MAGIC_NUMBER = b'3\r\r\n'


def main():
    args = parse_args()
    if importlib.util.MAGIC_NUMBER != EXPECTED_MAGIC_NUMBER:
        CANT = ("buildPython version is {}.{}.{}, so can't compile '{}' files to .pyc format."
                .format(*sys.version_info[:3], args.tag))
        SEE = "See https://chaquo.com/chaquopy/doc/current/android.html#android-bytecode."
        if args.required:
            print(" ".join([CANT, SEE]), file=sys.stderr)
            sys.exit(1)
        else:
            print(" ".join(["Warning:", CANT, "This will cause the app to start up slower "
                            "and use more storage space.", SEE]))
            sys.exit(0)

    os.chdir(args.dir)  # Don't store build machine paths in the .pyc files.
    if not compile_dir(".", maxlevels=sys.maxsize, legacy=True,
                       quiet=(2 if args.quiet else 1)):
        print("Warning: some files could not be compiled to .pyc format.")

    # Remove .py files which were successfully compiled.
    for dirpath, dirnames, filenames in os.walk(args.dir):
        for filename in filenames:
            if filename.endswith(".py"):
                full_filename = join(dirpath, filename)
                if isfile(full_filename + "c"):
                    os.remove(full_filename)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--required", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("dir")
    return ap.parse_args()


if __name__ == "__main__":
    main()
