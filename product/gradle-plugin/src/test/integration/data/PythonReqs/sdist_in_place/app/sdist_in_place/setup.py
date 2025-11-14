import os
import tempfile
from setuptools import setup


expected = os.path.realpath(
    f"{tempfile.gettempdir()}/test_gradle_plugin/"
    f"{os.environ['CHAQUOPY_AGP_VERSION']}/PythonReqs/sdist_in_place/project/"
    f"app/sdist_in_place/setup.py"
)
assert __file__ == expected, f"{__file__=}, {expected=}"

setup(
    name="sdist_in_place",
    version="1.2.3",
)
