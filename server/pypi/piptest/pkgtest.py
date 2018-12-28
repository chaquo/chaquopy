#!/usr/bin/env python3.6

import argparse
from datetime import datetime
from distutils.dir_util import copy_tree
import subprocess
import os
from os.path import abspath, basename, dirname, exists
import sys


PROGRAM_NAME = basename(__file__)
pkgtest_dir = abspath(dirname(__file__))


def main():
    args = parse_args()
    print(args.package + ": ", end="")
    sys.stdout.flush()

    version_short = args.version.rpartition(".")[0]
    build_dir = ensure_empty(f"{pkgtest_dir}/build/{version_short}/{args.package}")
    copy_tree(f"{pkgtest_dir}/src", build_dir)

    log_dir = ensure_dir(f"{pkgtest_dir}/log/{version_short}")
    with open(f"{log_dir}/{args.package}.txt", "w", buffering=1) as log_file:
        print("{}: installing {} with Python version {} at {}"
              .format(PROGRAM_NAME, args.package, args.version,
                      datetime.utcnow().isoformat(timespec="seconds") + "Z"), file=log_file)
        os.chdir(build_dir)
        os.environ.update(pkgtest_verbose=str(args.v), pkgtest_version=args.version,
                          pkgtest_package=args.package)
        gradlew = "gradlew.bat" if sys.platform.startswith("win") else "./gradlew"
        process = subprocess.Popen([gradlew,"--console", "plain", "--stacktrace", 
                                    "generateDebugPythonRequirementsAssets"],
                                   stdout=log_file, stderr=subprocess.STDOUT, errors="replace")
        status = process.wait(timeout=300)

    if status == 0:
        print("ok")
        os.chdir(pkgtest_dir)
        rmtree(build_dir)
    else:
        print("FAIL")
        sys.exit(1)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", action="store_true", help="Log verbosely")
    ap.add_argument("--version", required=True, help="Python version")
    ap.add_argument("package")
    return ap.parse_args()


def ensure_empty(dir_name):
    if exists(dir_name):
        rmtree(dir_name)
    return ensure_dir(dir_name)

def ensure_dir(dir_name):
    if not exists(dir_name):
        os.makedirs(dir_name)
    return dir_name

# shutil.rmtree is unreliable on Windows: it frequently fails with Windows error 145 (directory
# not empty), even though it has already removed everything from that directory.
def rmtree(path):
    subprocess.check_call(["rm", "-rf", path])
        

if __name__ == "__main__":
    main()
