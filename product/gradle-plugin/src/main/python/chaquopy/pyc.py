#!/usr/bin/env python3

"""Copyright (c) 2019 Chaquo Ltd. All rights reserved."""

# Keep valid Python 2 syntax so we can produce an error message.
from __future__ import absolute_import, division, print_function

# Do this as early as possible to minimize the chance of something else going wrong and causing
# a less comprehensible error message.
from .util import check_build_python
check_build_python()

import argparse
import importlib.util
import os
from os.path import abspath, join
import py_compile
import shutil
import sys
import warnings


# See importlib._bootstrap_external.MAGIC_NUMBER.
EXPECTED_MAGIC_NUMBER = (3413).to_bytes(2, 'little') + b'\r\n'


def main():
    args = parse_args()
    if importlib.util.MAGIC_NUMBER != EXPECTED_MAGIC_NUMBER:
        if args.warning:
            # Causes Android Studio to show the line as a warning in tree view.
            print("Warning: ", end="")
        print("buildPython version is {}.{}.{}".format(*sys.version_info[:3]),
              "with bytecode magic number {}".format(importlib.util.MAGIC_NUMBER.hex()),
              "(expected number is {})".format(EXPECTED_MAGIC_NUMBER.hex()))
        sys.exit(1)

    if args.quiet:
        warnings.filterwarnings("ignore", category=SyntaxWarning)

    # py_compile uses _bootstrap_external._write_atomic, which writes to a temporary file with
    # a longer name, potentially pushing us over the Windows 260-character filename limit. But
    # since there are no other processes accessing the directory, atomicity doesn't matter.
    try:
        from importlib import _bootstrap_external
        if hasattr(_bootstrap_external, "_write_atomic"):
            def _write_atomic_override(path, data, mode=0o666):
                with open(path, "wb") as f:
                    f.write(data)
                os.chmod(path, mode)
            _bootstrap_external._write_atomic = _write_atomic_override
        else:
            print("Warning: importlib._bootstrap_external._write_atomic doesn't exist")
    except ImportError:
        print("Warning: importlib._bootstrap_external doesn't exist")

    os.chdir(args.in_dir)
    for dirpath, dirnames, filenames in os.walk(os.getcwd()):
        os.makedirs(join(args.out_dir, dirpath), exist_ok=True)
        for filename in filenames:
            in_filename = join(dirpath, filename)
            out_filename = join(args.out_dir, in_filename)
            compiled = False
            if filename.endswith(".py"):
                try:
                    py_compile.compile(in_filename, out_filename + "c", doraise=True)
                    compiled = True
                except py_compile.PyCompileError as e:
                    if not args.quiet:
                        print(e)
            if (not compiled) and (args.in_dir != args.out_dir):
                shutil.copy(in_filename, out_filename)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--warning", action="store_true")
    ap.add_argument("in_dir", type=abspath)
    ap.add_argument("out_dir", type=abspath, nargs="?")
    args = ap.parse_args()
    if args.out_dir is None:
        args.out_dir = args.in_dir
    return args


if __name__ == "__main__":
    main()
