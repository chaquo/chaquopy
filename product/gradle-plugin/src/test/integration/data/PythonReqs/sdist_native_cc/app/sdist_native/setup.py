from setuptools import setup
import sys

if "sdist" not in sys.argv:
    # Simulate a package which tries to run the compiler directly, without going through
    # distutils at all.
    import os
    import subprocess
    compiler = os.environ.get("CC", "gcc")
    try:
        subprocess.check_call([compiler])
    except OSError:
        # FileNotFoundError message doesn't contain the filename on Windows.
        print("Failed to run " + compiler)
        raise

setup(
    name="sdist_native_cc",
    version="1.0",
)
