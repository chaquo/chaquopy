# Based on https://cython.readthedocs.io/en/stable/src/quickstart/build.html#building-a-cython-module-using-distutils

from setuptools import setup
from Cython.Build import cythonize

setup(
    name='cython-example',
    version='1.0',
    ext_modules=cythonize("hello.pyx"),
)
