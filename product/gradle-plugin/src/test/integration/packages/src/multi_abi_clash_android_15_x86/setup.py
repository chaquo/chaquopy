from setuptools import Extension, find_packages, setup

setup(
    name="multi_abi_clash",
    version="0.1",
    packages=find_packages(),
    ext_modules=[Extension("multi_abi_1_x86", ["multi_abi_1_x86.c"])],
)
