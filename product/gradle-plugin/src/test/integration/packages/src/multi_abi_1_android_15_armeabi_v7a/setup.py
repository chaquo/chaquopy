from setuptools import Extension, find_packages, setup

setup(
    name="multi_abi_1",
    version="0.1",
    packages=find_packages(),
    ext_modules=[Extension("multi_abi_1_armeabi_v7a", ["multi_abi_1_armeabi_v7a.c"])],
)
