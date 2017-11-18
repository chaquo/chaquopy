#!/usr/bin/env python3

import argparse
import os
from os.path import abspath, basename, dirname, exists, join
import shlex
import subprocess
import sys

import attr


PROGRAM_NAME = basename(__file__)
PYPI_DIR = abspath(dirname(__file__))

HOST_PLATFORM = "linux-x86_64"
GCC_VERSION = "4.9"

@attr.s
class Abi:
    name = attr.ib()
    platform = attr.ib()
    toolchain = attr.ib()
    tool_prefix = attr.ib()

ABIS = {abi.name : abi for abi in [
    Abi("armeabi-v7a", "arm", "arm-linux-androideabi", "arm-linux-androideabi"),
    Abi("x86", "x86", "x86", "i686-linux-android"),
]}


def main():
    try:
        args = parse_args()
        abi = ABIS[args.abi]

        package_dir = join(PYPI_DIR, "packages", args.package)
        if not exists(package_dir):
            raise CommandError(f"{package_dir} does not exist (package name is case-sensitive)")
        build_dir = join(package_dir, "build")
        if not exists(build_dir):
            run(f"mkdir {build_dir}")

        cd(build_dir)
        sdist_dir = unpack_sdist(args)


    except CommandError as e:
        log(str(e))
        sys.exit(1)



def unpack_sdist(args):
    sdist_dir = f"{args.package}-{args.version}"
    if exists(sdist_dir):
        run(f"rm -rf {sdist_dir}")

    sdist_filename = find_sdist(sdist_dir)
    if sdist_filename:
        log(f"Found existing sdist {sdist_filename}")
    else:
        run(f"pip download --no-binary :all: {args.package}=={args.version}")
        sdist_filename = find_sdist(sdist_dir)
        if not sdist_filename:
            raise CommandError("Still can't find sdist: maybe it has an unknown filename extension")

    if sdist_filename.endswith("zip"):
        run(f"unzip -q {sdist_filename}")
    else:
        run(f"tar -xf {sdist_filename}")
    return sdist_dir


def find_sdist(sdist_dir):
    for ext in ["zip", "tar.gz", "tgz", "tar.bz2", "tbz2", "tar.xz", "txz"]:
        filename = f"{sdist_dir}.{ext}"
        if exists(filename):
            return filename


def parse_args():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--help", action="help", help=argparse.SUPPRESS)
    ap.add_argument("--ndk", metavar="DIR", help="Path to NDK (default: $ANDROID_HOME/ndk-bundle)")
    ap.add_argument("--python", metavar="DIR", required=True,
                    help="Path to Python to build against. Must follow Crystax "
                    "'sources/python' subdirectory layout, containing 'include' and 'libs'.")
    ap.add_argument("--abi", metavar="ABI", required=True, choices=sorted(ABIS.keys()),
                    help="Choices: %(choices)s")
    ap.add_argument("--api-level", metavar="N", default="15", help="Default: %(default)s")
    ap.add_argument("package")
    ap.add_argument("version")
    args = ap.parse_args()

    if not args.ndk:
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            raise CommandError("Can't find NDK: either pass --ndk or set $ANDROID_HOME")
        args.ndk = join(android_home, "ndk-bundle")
    if not exists(args.ndk):
        raise CommandError(f"Can't find NDK: {args.ndk} does not exist")

    return args


def run(command):
    log(command)
    subprocess.run(shlex.split(command), check=True)


def cd(new_dir):
    log(f"cd {new_dir}")
    os.chdir(new_dir)


def log(s):
    print(f"{PROGRAM_NAME}: {s}")


class CommandError(Exception):
    pass



if __name__ == "__main__":
    main()
