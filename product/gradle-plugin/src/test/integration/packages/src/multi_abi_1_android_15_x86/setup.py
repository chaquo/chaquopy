from setuptools import Extension, find_packages, setup

setup(
    name="multi_abi_1",
    version="0.1",
    packages=find_packages(),

    # We use ext_modules so that the wheel will have "Root-Is-Purelib: false".
    ext_modules=[Extension("module_x86", ["module_x86.c"]),
                 Extension("pkg.submodule_x86", ["pkg/submodule_x86.c"])],
)
