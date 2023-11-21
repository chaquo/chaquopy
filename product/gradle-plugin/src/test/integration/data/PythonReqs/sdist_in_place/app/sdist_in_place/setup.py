import os
from setuptools import Extension, setup

assert __file__ == os.path.abspath(
    f"{os.environ['integration_dir']}/../../../build/test/integration/"
    f"{os.environ['CHAQUOPY_AGP_VERSION']}/PythonReqs/sdist_in_place/project/"
    f"app/sdist_in_place/setup.py"
), __file__

setup(
    name="sdist_in_place",
    version="1.2.3",
)
