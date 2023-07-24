#!/usr/bin/env python3

import argparse
import ensurepip
from glob import glob
import os
from os.path import abspath, dirname, exists
from shlex import split
import subprocess
import venv


PYPI_DIR = abspath(dirname(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("build_env_dir")
args = ap.parse_args()

# Installing Python's bundled pip and setuptools into the environment is pointless since
# we're just going to replace them anyway. Instead, use the bundled pip to install our
# requirements file directly. This saves about 3.5 seconds on Python 3.8, and 6 seconds
# on Python 3.11.
assert not exists(args.build_env_dir)
venv.create(args.build_env_dir, with_pip=False)

pip_whl, = glob(f"{ensurepip.__path__[0]}/_bundled/pip-*.whl")  # Note comma
env = os.environ.copy()
env["PYTHONPATH"] = pip_whl

subprocess.run(
    split(f"{args.build_env_dir}/bin/python -m") +
    split(f"pip install -r {PYPI_DIR}/requirements-build-env.txt"),
    env=env, check=True)
