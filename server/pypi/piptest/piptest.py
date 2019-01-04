#!/usr/bin/env python3

import argparse
from datetime import datetime
from distutils.dir_util import copy_tree
import os
from os.path import abspath, basename, dirname, exists, join
from shutil import rmtree
import subprocess
import sys


PROGRAM_NAME = basename(__file__)
piptest_dir = abspath(dirname(__file__))


def main():
    args = parse_args()
    print(args.package + ": ", end="")
    sys.stdout.flush()

    build_dir = ensure_empty(join(piptest_dir, "build", args.package))
    copy_tree(join(piptest_dir, "src"), build_dir)

    log_dir = ensure_dir(join(piptest_dir, "log"))
    with open(join(log_dir, args.package + ".txt"), "wb", buffering=0) as log_file:
        log_file.write(
            "{}: testing '{}' at {}\n"
            .format(PROGRAM_NAME, args.package, datetime.utcnow().isoformat() + "Z")
            .encode("UTF-8"))
        os.chdir(build_dir)
        os.environ.update(piptest_verbose=str(args.v), piptest_package=args.package)
        try:
            subprocess.run(["./gradlew", "--console", "plain", "--stacktrace",
                            "generateDebugPythonRequirementsAssets"],
                           stdout=log_file, stderr=subprocess.STDOUT, timeout=300, check=True)
        except subprocess.TimeoutExpired:
            print("TIMEOUT")
            sys.exit(1)
        except subprocess.CalledProcessError:
            print("FAIL")
            sys.exit(1)
        else:
            print("OK")
            os.chdir(piptest_dir)
            rmtree(build_dir)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", action="store_true", help="Log verbosely")
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


if __name__ == "__main__":
    main()
