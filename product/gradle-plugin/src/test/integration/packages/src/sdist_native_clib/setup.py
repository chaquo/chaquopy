from setuptools import setup

setup(
    name="sdist_native_clib",
    version="1.0",
    libraries=[("test", {"sources": ["libtest.c"]})]
)
