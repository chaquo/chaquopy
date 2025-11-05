from setuptools import setup
import sys

if "sdist" not in sys.argv:
    # Simulate a package which tries to run the compiler directly, without going through
    # distutils at all.
    import os
    import subprocess
    compiler = os.environ.get("CC", "gcc")
    subprocess.check_call([compiler])

setup(
    name="sdist_native_cc",
    version="1.0",
)
