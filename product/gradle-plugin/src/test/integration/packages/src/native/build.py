#!/usr/bin/env python3
# This file requires Python 3.6 or later.

import argparse
import os
from os.path import abspath, basename, dirname, isdir, join
import shutil
import subprocess
import sys
from textwrap import dedent


ap = argparse.ArgumentParser()
ap.add_argument("setup_command")
ap.add_argument("name")
ap.add_argument("version")
ap.add_argument("--package", dest="packages", default=[], action="append")
ap.add_argument("--disable-sdist-install", action="store_true")
args = ap.parse_args()

src_dir = abspath(dirname(__file__))
for name in os.listdir(src_dir):
    if name not in [".gitignore", basename(__file__)]:
        abs_name = join(src_dir, name)
        (shutil.rmtree if isdir(abs_name) else os.remove)(abs_name)

for pkg_name in args.packages:
    pkg_dir = join(src_dir, pkg_name)
    os.mkdir(pkg_dir)
    with open(join(pkg_dir, "__init__.py"), "w") as init_file:
        print("# Version " + args.version, file=init_file)

setup_filename = join(src_dir, "setup.py")
with open(setup_filename, "w") as setup_file:
    setup_file.write(dedent("""
        from setuptools import setup
        import sys
    """))

    if args.disable_sdist_install:
        setup_file.write(dedent("""
            # This script can be used to build wheels, but will fail to install from an sdist.
            if any(word in ["egg_info", "install"] for word in sys.argv):
                raise Exception("Simulate install failure")
        """))

    setup_file.write(dedent(f"""
        setup(
            name="{args.name}",
            version="{args.version}",
            packages={args.packages},
        )
    """))

setup_cmdline = [sys.executable, setup_filename, args.setup_command]
if args.setup_command == "bdist_wheel":
    setup_cmdline.append("--universal")
subprocess.check_call(setup_cmdline)
