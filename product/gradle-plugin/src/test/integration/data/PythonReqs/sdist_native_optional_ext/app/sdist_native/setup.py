from distutils.core import Extension, setup
from distutils.errors import DistutilsPlatformError

from distutils.command.build_ext import build_ext as build_ext_original


# See notes in setuptools/monkey.py. This is the lowest-level location I've seen which a
# package wraps with an exception handler in order to provide a pure-Python fallback.
# Higher-level locations like build_ext.run() and setup() itself should therefore also be
# covered by this test.
class build_ext_override(build_ext_original):
    def build_extension(self, ext):
        try:
            return build_ext_original.build_extension(self, ext)
        except DistutilsPlatformError:
            pass


setup(
    name="sdist_native_optional_ext",
    version="1.0",
    cmdclass={"build_ext": build_ext_override},
    ext_modules=[Extension("ext_module", ["ext_module.c"])],
    py_modules=["sdist_native_optional_ext"]
)
