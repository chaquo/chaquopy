from setuptools import Extension, find_packages, setup

setup(
    name="duplicate_filenames_native",
    version="1.0",
    packages=find_packages(),

    # We use ext_modules so that the wheel will have "Root-Is-Purelib: false".
    ext_modules=[Extension("native_armeabi_v7a", ["native_armeabi_v7a.c"])],
)
