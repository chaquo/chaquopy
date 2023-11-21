#!/usr/bin/env python3

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


# See the list in importlib/_bootstrap_external.py.
MAGIC = {
    "3.7": 3394,
    "3.8": 3413,
    "3.9": 3425,
    "3.10": 3439,
    "3.11": 3495,
    "3.12": 3531,
}


def main():
    args = parse_args()
    if importlib.util.MAGIC_NUMBER != MAGIC[args.python].to_bytes(2, "little") + b"\r\n":
        # Messages should be formatted the same as those from the Gradle plugin.
        message = (
            "Failed to compile to .pyc format: buildPython version {}.{}.{} is incompatible. "
            "See https://chaquo.com/chaquopy/doc/current/android.html#android-bytecode."
            .format(*sys.version_info[:3]))
        if args.warning:
            print("Warning:", message)
            sys.exit(0)
        else:
            print(message)
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


if __name__ == "__main__":
    main()
