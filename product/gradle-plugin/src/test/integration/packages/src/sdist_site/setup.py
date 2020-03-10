from importlib import import_module
import os
from setuptools import setup
import sys

if "sdist" not in sys.argv:
    import_module(os.environ["CHAQUOPY_PKG_NAME"])

setup(
    name="sdist_site",
    version="1.0",
)
