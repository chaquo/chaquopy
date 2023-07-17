#!/usr/bin/env python3

import argparse
from os.path import abspath, dirname
import re

parser = argparse.ArgumentParser()
mode_group = parser.add_mutually_exclusive_group(required=True)
mode_group.add_argument("--short", action="store_true")
mode_group.add_argument("--long", action="store_true")
args = parser.parse_args()

product_dir = abspath(f"{dirname(__file__)}/../product")
for line in open(f"{product_dir}/buildSrc/src/main/java/com/chaquo/python/Common.java"):
    match = re.search(r'PYTHON_VERSIONS.put\("(\d+)\.(\d+)\.(\d+)", "(\d+)"\)', line)
    if match:
        major, minor, micro, build = match.groups()
        if args.short:
            print(f"{major}.{minor}")
        elif args.long:
            print(f"{major}.{minor}.{micro}-{build}")
        else:
            raise AssertionError()

