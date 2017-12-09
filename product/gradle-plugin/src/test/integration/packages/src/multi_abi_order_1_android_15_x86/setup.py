from setuptools import Extension, setup

setup(
    name="multi_abi_order",
    version="0.1",
    ext_modules=[Extension("multi_abi_order_x86", ["multi_abi_order_x86.c"])],
)
