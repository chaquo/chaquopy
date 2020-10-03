import os
from setuptools import setup


setup(
    name="chaquopy_dir",
    version="1.0",
    data_files=[(dirpath, [f"{dirpath}/{name}" for name in filenames])
                for dirpath, dirnames, filenames in os.walk("chaquopy")]
)
