from distutils.sysconfig import customize_compiler
from setuptools import setup
import sys

if "sdist" not in sys.argv:
    # Simulate a package which tries to run the compiler without going through
    # build_ext or build_clib.
    import distutils.ccompiler
    compiler = distutils.ccompiler.new_compiler()
    customize_compiler(compiler)
    compiler.compile(["test.c"])  # Doesn't matter whether it exists.

setup(
    name="sdist_native_compiler",
    version="1.0",
)
