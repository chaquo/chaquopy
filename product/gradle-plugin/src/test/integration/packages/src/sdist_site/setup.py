
from setuptools import setup
import sys

if "sdist" not in sys.argv:
    import javaproperties  # noqa: F401

setup(
    name="sdist_site",
    version="1.0",
)
