#!/usr/bin/env python3

import sys
from setuptools import setup


assert len(sys.argv) == 2
abi = sys.argv[1]
sys.argv[1:] = ["bdist_wheel", "--plat-name", f"android_24_{abi}"]

setup(
    name="py3_none",
    version="0.0.1",
    py_modules=[abi],
)
