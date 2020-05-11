#!/usr/bin/env python

import argparse
import os
from os.path import abspath, basename, dirname, isdir, join
from setuptools import setup
import shutil
import sys


ap = argparse.ArgumentParser()
ap.add_argument("--version", default="1.0")
ap.add_argument("--comment")
ap.add_argument("name")
args = ap.parse_args()
sys.argv[1:] = ["bdist_wheel", "--universal"]

src_dir = abspath(dirname(__file__))
for filename in os.listdir(src_dir):
    if filename not in [".gitignore", basename(__file__)]:
        abs_filename = join(src_dir, filename)
        (shutil.rmtree if isdir(abs_filename) else os.remove)(abs_filename)

with open(args.name + ".py", "w") as py_file:
    print("#", args.comment or args.name, file=py_file)

setup(
    name=args.name,
    version=args.version,
    py_modules=[args.name],
)
