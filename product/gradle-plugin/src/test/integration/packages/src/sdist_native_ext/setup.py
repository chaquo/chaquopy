from setuptools import Extension, setup

setup(
    name="sdist_native_ext",
    version="1.0",
    ext_modules=[Extension("ext_module", ["ext_module.c"])]
)
