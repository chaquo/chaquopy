from setuptools import setup
import sys

if "sdist" in sys.argv:
    py_modules = ["two", "three"]
else:
    py_modules = ["two" if (sys.version_info[0] == 2) else "three"]

setup(
    name="buildpython_default",
    version="0.0.1",
    py_modules=py_modules
)
