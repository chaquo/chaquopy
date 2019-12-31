#!/usr/bin/env python3
#
# On Unix: ln -s ../../hooks/pre-commit.py .git/hooks/pre-commit
# On Windows (requires admin shell): mklink .git\hooks\pre-commit ..\..\hooks\pre-commit.py

import argparse
import configparser
from fnmatch import fnmatch
from os.path import basename, dirname, isdir
import shlex
import subprocess
from subprocess import run
import sys


ap = argparse.ArgumentParser()
ap.add_argument("dir", nargs="?")
args = ap.parse_args()

cfg = configparser.ConfigParser()
with open("setup.cfg") as cfg_file:
    cfg.read_file(cfg_file)
exclude = [pattern.strip() for pattern in cfg["flake8"]["exclude"].split(",")
           if pattern.strip()]

def is_excluded(name):
    while name:
        if any(fnmatch(name, ex) or fnmatch(basename(name), ex)
               for ex in exclude):
            return True
        name = dirname(name)
    return False

cmd = shlex.split("git ls-files --cached --others --exclude-standard " + args.dir if args.dir
                  else "git diff --cached --diff-filter=d --name-only")
files = [name for name in
         run(cmd, stdout=subprocess.PIPE, check=True, universal_newlines=True).stdout.splitlines()
         if not is_excluded(name)
         and not isdir(name)]  # Submodule

result = 0
if files:
    if not run(["grep", "-Hniw",  # -w prevents matching JUnit's @FixMethodOrder.
                "FIX" + "ME"]     # Avoid matching this file.
               + files).returncode:
        result = 1

    py_files = [name for name in files if name.endswith(".py")]
    if py_files:
        if run(["flake8"] + py_files).returncode:
            result = 1

sys.exit(result)
