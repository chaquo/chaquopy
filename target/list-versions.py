#!/usr/bin/env python3

import argparse
from os.path import abspath, dirname
import re

parser = argparse.ArgumentParser()
mode_group = parser.add_mutually_exclusive_group(required=True)
mode_group.add_argument("--default", action="store_true")
mode_group.add_argument("--minor", action="store_true")
mode_group.add_argument("--micro", action="store_true")
mode_group.add_argument("--build", action="store_true")
args = parser.parse_args()
versions_seen = set()

product_dir = abspath(f"{dirname(__file__)}/../product")
lines = []
for line in open(
    f"{product_dir}/buildSrc/src/main/java/com/chaquo/python/internal/Common.java"
):
    if args.default:
        match = re.search(r'DEFAULT_PYTHON_VERSION = "(.+)"', line)
        if match:
            lines.append(match[1])
            break

    elif "PYTHON_VERSIONS.put" in line:
        if not (match := re.search(
            r'PYTHON_VERSIONS.put\("(\d+)\.(\d+)\.(\w+)", "(\d+)"\)', line
        )):
            raise ValueError(f"couldn't parse {line!r}")
        major, minor, micro, build = match.groups()

        version = f"{major}.{minor}"
        if version in versions_seen:
            raise ValueError(f"more than one entry for Python {version}")
        versions_seen.add(version)

        if args.micro or args.build:
            version += f".{micro}"
        if args.build:
            version += f"-{build}"
        lines.append(version)

assert lines
print("\n".join(lines))
