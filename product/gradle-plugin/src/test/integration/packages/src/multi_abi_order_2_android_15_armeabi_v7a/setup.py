from setuptools import Extension, setup

setup(
    name="multi_abi_order",
    version="0.2",
    ext_modules=[Extension("multi_abi_order_armeabi_v7a", ["multi_abi_order_armeabi_v7a.c"])],
)
