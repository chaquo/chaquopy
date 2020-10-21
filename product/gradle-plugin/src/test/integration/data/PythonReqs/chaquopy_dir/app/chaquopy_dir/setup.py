import os
from setuptools import setup


setup(
    name="chaquopy_dir",
    version="1.0",
    packages=["chaquopy"],
    package_data={"chaquopy": ["*", "*/*", "*/*/*"]}
)
