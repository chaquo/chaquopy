#!/usr/bin/env python3

import argparse
import importlib.util
import os
from os.path import abspath, join
import py_compile
import shutil
import sys
import warnings


# See the CPython source code in Include/internal/pycore_magic_number.h or
# Lib/importlib/_bootstrap_external.py.
MAGIC = {
    "3.10": 3439,
    "3.11": 3495,
    "3.12": 3531,
    "3.13": 3571,
    "3.14": 3627,
}


def main():
    args = parse_args()
    check_magic(args)

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

    for dirpath, dirnames, filenames in os.walk(args.in_dir):
        os.makedirs(join(args.out_dir, dirpath), exist_ok=True)
        for filename in filenames:
            in_filename = join(dirpath, filename)
            out_filename = join(args.out_dir, in_filename)
            compiled = False
            if filename.endswith(".py"):
                try:
                    # We use the `dfile` argument to make the build reproducible. Its exact
                    # value doesn't matter, since it'll be overridden at runtime by
                    # SourcelessAssetLoader.get_code.
                    py_compile.compile(in_filename, out_filename + "c", dfile=filename,
                                       doraise=True)
                    compiled = True
                except py_compile.PyCompileError as e:
                    if not args.quiet:
                        print(e)
            if (not compiled) and (args.in_dir != args.out_dir):
                shutil.copy(in_filename, out_filename)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", required=True)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--warning", action="store_true")
    ap.add_argument("in_dir", type=abspath)
    ap.add_argument("out_dir", type=abspath, nargs="?")
    args = ap.parse_args()
    if args.out_dir is None:
        args.out_dir = args.in_dir
    return args


# Since the Python version has already been checked by the Gradle plugin, this should
# never fail unless the magic number changes after a Python minor version goes stable.
def check_magic(args):
    magic_bytes = importlib.util.MAGIC_NUMBER
    if len(magic_bytes) != 4 or magic_bytes[-2:] != b"\r\n":
        error(args, f"magic number {magic_bytes} is in an unknown format")

    magic_int = int.from_bytes(magic_bytes[:2], "little")
    if magic_int != MAGIC[args.python]:
        error(args, f"magic number is {magic_int}; expected {MAGIC[args.python]}")


def error(args, message):
    # Messages should be formatted the same as those from the Gradle plugin.
    message = (
        f"Failed to compile to .pyc format: {message}. "
        f"See https://chaquo.com/chaquopy/doc/current/android.html#android-bytecode."
    )
    if args.warning:
        print("Warning:", message)
        sys.exit(0)
    else:
        print(message, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
