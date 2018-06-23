from distutils.core import setup
from distutils.errors import DistutilsPlatformError
from distutils.sysconfig import customize_compiler
import sys

if "sdist" not in sys.argv:
    # Simulate a package which tries to run the compiler without going through
    # build_ext or build_clib, but handles the case where it fails.
    import distutils.ccompiler
    compiler = distutils.ccompiler.new_compiler()
    customize_compiler(compiler)
    try:
        compiler.compile(["test.c"])  # Doesn't matter whether it exists.
    except DistutilsPlatformError:
        pass

setup(
    name="sdist_native_optional_compiler",
    version="1.0",
    py_modules=["sdist_native_optional_compiler"]
)
