from __future__ import absolute_import, division, print_function

from setuptools import setup
import os
from os.path import abspath, dirname, join
import shutil
import sys

PREFIX = "native"

# This script can be used to build wheels, but will fail to install from an sdist.
if not any(word in ["sdist", "bdist_wheel"] for word in sys.argv):
    raise Exception("Simulate install failure")

# distutils seems very keen to include leftovers of previous builds, whether we asked for them
# or not.
src_dir = abspath(dirname(__file__))
for name in os.listdir(src_dir):
    if name.startswith(PREFIX) or name in ["build", "dist"]:
        shutil.rmtree(join(src_dir, name))

# Generate dists like this:
#   python setup.py {sdist|bdist_wheel} <name> <version> <package-suffix>
suffix = sys.argv.pop()
version = sys.argv.pop()
name = sys.argv.pop()
assert name.startswith(PREFIX)

pkg_name = "{}_{}".format(name, suffix)
pkg_dir = join(dirname(__file__), pkg_name)
os.mkdir(pkg_dir)
with open(join(pkg_dir, "__init__.py"), "w") as init_file:
    print("# Version " + version, file=init_file)

setup(
    name=name,
    version=version,
    packages=[pkg_name]
)
