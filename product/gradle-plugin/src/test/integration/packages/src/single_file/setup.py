#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import argparse
import os
from os.path import abspath, basename, dirname, isdir, join
from setuptools import setup
import shutil
import sys


ap = argparse.ArgumentParser()
ap.add_argument("name")
args = ap.parse_args()
sys.argv[1:] = ["bdist_wheel", "--universal"]

src_dir = abspath(dirname(__file__))
for filename in os.listdir(src_dir):
    if filename not in [".gitignore", basename(__file__)]:
        abs_filename = join(src_dir, filename)
        (shutil.rmtree if isdir(abs_filename) else os.remove)(abs_filename)

with open(args.name + ".py", "w") as py_file:
    print("#", args.name, file=py_file)

setup(
    name=args.name,
    version="1.0",
    py_modules=[args.name],
)
