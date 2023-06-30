#!/usr/bin/env python3.8

import argparse
from datetime import datetime
from distutils.dir_util import copy_tree
import io
import os
from os.path import abspath, basename, dirname, exists, join
from shutil import rmtree
import subprocess
import sys


PROGRAM_NAME: str = basename(__file__)
TIME_LIMIT: int = 300  # seconds
piptest_dir: str = abspath(dirname(__file__))


def main():
    args = parse_args()
    print(f"{args.package}: start", flush=True)

    build_dir: str = ensure_empty(join(piptest_dir, "build", args.package))
    copy_tree(join(piptest_dir, "src"), build_dir)

    log_dir: str = ensure_dir(join(piptest_dir, "log"))
    with open(join(log_dir, args.package + ".txt"), "wb", buffering=0) as log_file:
        log_file_text = io.TextIOWrapper(log_file, write_through=True)
        timestamp: str = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        print(f"{PROGRAM_NAME}: testing '{args.package}' at {timestamp}", file=log_file_text)
        os.chdir(build_dir)
        os.environ.update(piptest_verbose=str(args.v), piptest_package=args.package)
        try:
            subprocess.run(["./gradlew", "--console", "plain", "--stacktrace",
                            "generateDebugPythonRequirementsAssets"],
                           stdout=log_file, stderr=subprocess.STDOUT, timeout=TIME_LIMIT,
                           check=True)
        except subprocess.TimeoutExpired:
            # To help search for failures, use the same "BUILD FAILED" phrase as Gradle.
            print(f"{PROGRAM_NAME}: BUILD FAILED: timeout after {TIME_LIMIT} seconds",
                  file=log_file_text)
            print(f"{args.package}: FAIL (timeout)")
            sys.exit(1)
        except subprocess.CalledProcessError:
            print(f"{args.package}: FAIL")
            sys.exit(1)
        else:
            print(f"{args.package}: PASS")
            os.chdir(piptest_dir)
            rmtree(build_dir)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", action="store_true", help="Log verbosely")
    ap.add_argument("package")
    return ap.parse_args()


def ensure_empty(dir_name: str) -> str:
    if exists(dir_name):
        rmtree(dir_name)
    return ensure_dir(dir_name)

def ensure_dir(dir_name: str) -> str:
    if not exists(dir_name):
        os.makedirs(dir_name)
    return dir_name


if __name__ == "__main__":
    main()
