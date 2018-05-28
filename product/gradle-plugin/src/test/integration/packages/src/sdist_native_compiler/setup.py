from setuptools import setup
import sys

if "sdist" not in sys.argv:
    # Simulate a package which tries to run the compiler directly, without going through
    # build_ext or build_clib.
    import distutils.ccompiler
    distutils.ccompiler.new_compiler()

setup(
    name="sdist_native_compiler",
    version="1.0",
)
