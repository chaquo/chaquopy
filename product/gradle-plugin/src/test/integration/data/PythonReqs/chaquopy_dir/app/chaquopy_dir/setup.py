from glob import glob
from setuptools import setup


setup(
    name="chaquopy_dir",
    version="1.0",
    data_files=[(dir_name, glob(f"{dir_name}/*.txt"))
                 for dir_name in ["chaquopy", "chaquopy/include", "chaquopy/lib"]]
)
