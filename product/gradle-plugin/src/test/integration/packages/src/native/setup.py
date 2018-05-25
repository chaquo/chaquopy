from setuptools import setup
import os
from os.path import dirname, exists, join
import sys

# Generate dists like this:
#   python setup.py clean {sdist|bdist_wheel} <name> <version> <package-suffix>
suffix = sys.argv.pop()
version = sys.argv.pop()
name = sys.argv.pop()

pkg_name = "{}_{}".format(name, suffix)
src_dir = join(dirname(__file__), pkg_name)
if not exists(src_dir):
    os.mkdir(src_dir)
    with open(join(src_dir, "__init__.py"), "w"):
        pass

setup(
    name=name,
    version=version,
    packages=[pkg_name]
)
