#!/usr/bin/env python3

# Always built as pure Python, but pure Python wheels aren't on PyPI:
#     pycparser

# Optionally built as pure Python, but pure Python wheels aren't on PyPI:
#     pyyaml (requires external library)
#     MarkupSafe (self-contained)

# Requires external library:
#     cffi: libffi
#     cryptography: openssl
#     pyzmq: libzmq
#     scrypt: openssl

# Self-contained:
#     numpy
#     regex
#     twisted
#     ujson


import argparse
import csv
import email.generator, email.parser
from glob import glob
import os
from os.path import abspath, basename, dirname, exists, isdir, join
from pkg_resources import parse_version
import re
import shlex
import subprocess
import sys
import sysconfig
from wheel.archive import archive_wheelfile
from wheel.bdist_wheel import bdist_wheel

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
    cflags = attr.ib(default="")
    ldflags = attr.ib(default="")

ABIS = {abi.name : abi for abi in [
    Abi("armeabi-v7a", "arm", "arm-linux-androideabi", "arm-linux-androideabi",
        cflags="-march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16",  # https://developer.android.com/ndk/
        ldflags="-march=armv7-a -Wl,--fix-cortex-a8"),               #   guides/standalone_toolchain.html
    Abi("x86", "x86", "x86", "i686-linux-android"),
]}


def main():
    try:
        args = parse_args()

        package_dir = join(PYPI_DIR, "packages", args.package)
        if not exists(package_dir):
            raise CommandError(f"{package_dir} does not exist (package name is case-sensitive)")
        build_dir = join(package_dir, "build")
        ensure_dir(build_dir)

        cd(build_dir)
        sdist_dir = unpack_sdist(args)
        cd(sdist_dir)
        apply_patches()
        wheel_filename = build_wheel(args)
        fix_wheel(args, wheel_filename)
    except CommandError as e:
        log(str(e))
        sys.exit(1)


def parse_args():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--help", action="help", help=argparse.SUPPRESS)
    ap.add_argument("-v", "--verbose", action="store_true", help="Log more detail")
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


def unpack_sdist(args):
    sdist_dir = f"{args.package}-{args.version}"
    if exists(sdist_dir):
        run(f"rm -rf {sdist_dir}")

    sdist_filename = find_sdist(sdist_dir)
    if sdist_filename:
        log(f"Found existing sdist")
    else:
        run(f"pip download --no-binary :all: {args.package}=={args.version}")
        sdist_filename = find_sdist(sdist_dir)
        if not sdist_filename:
            raise CommandError("Can't find downloaded sdist: maybe it has an unknown filename extension")

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


def apply_patches():
    patches_dir = "../../patches"
    if exists(patches_dir):
        for patch_filename in os.listdir(patches_dir):
            run(f"patch -t -p1 -i {patches_dir}/{patch_filename}")


# The environment variables set in this function are used for native builds by
# distutils.sysconfig.customize_compiler. We define values for all the overridable variables, but
# some are not overridable in Python 3.6 (e.g. OPT and CONFIGURE_CFLAGS). We also define some
# common variables like LD and STRIP which aren't used by distutils, but might be used by custom
# build scripts.
def build_wheel(args):
    env = get_env(args)
    if args.verbose:
        for name in sorted(env.keys()):
            log(f"{name}='{env[name]}'")
    os.environ.update(env)

    run(f"pip wheel{' -v' if args.verbose else ''} --no-deps --build-option --universal -e .")
    wheel_filenames = glob("*.whl")
    if len(wheel_filenames) != 1:
        raise CommandError(f"Found {len(wheel_filenames)} .whl files: expected exactly 1")
    return wheel_filenames[0]


def get_env(args):
    env = {}
    abi = ABIS[args.abi]

    tool_dir = f"{args.ndk}/toolchains/{abi.toolchain}-{GCC_VERSION}/prebuilt/{HOST_PLATFORM}/bin"
    for tool in ["ar", "as", ("cc", "gcc"), "cpp", ("cxx", "g++"), "ld", "nm", "ranlib",
                 "readelf", "strip"]:
        var, suffix = (tool, tool) if isinstance(tool, str) else tool
        filename = f"{tool_dir}/{abi.tool_prefix}-{suffix}"
        assert_exists(filename)
        env[var.upper()] = filename
    env["LDSHARED"] = f"{env['CC']} -shared"

    # Includes are in order of priority: see https://gcc.gnu.org/onlinedocs/gcc/Directory-Options.html
    ipython = f"{args.python}/include/python"
    isystem = f"{args.ndk}/sysroot/usr/include/{abi.tool_prefix}"
    isysroot = f"{args.ndk}/sysroot"                                                # includes
    idirafter = f"{PYPI_DIR}/idirafter"
    sysroot = f"{args.ndk}/platforms/android-{args.api_level}/arch-{abi.platform}"  # libs
    for dirname in [ipython, isystem, isysroot, idirafter, sysroot]:
        assert_isdir(dirname)
    env["CFLAGS"] = (f"-I{ipython} -isystem {isystem} -isysroot {isysroot} -idirafter {idirafter} "
                     f"--sysroot {sysroot} {abi.cflags}")

    # FIXME -lm renders a NumPy patch redundant
    env["LDFLAGS"] = f"-lm -L{libpython_dir(args)} -lpython{libpython_version(args)} {abi.ldflags}"

    # Clear all unused overridable variables to prevent the host Python values (if any) from taking
    # effect.
    for var in ["ARFLAGS", "CPPFLAGS"]:
        env[var] = ""

    return env


# The bdist_wheel command only has limited ability to set the compatibility tags, so we have to fix
# things up afterwards.
def fix_wheel(args, in_filename):
    out_dir = "../../dist"
    ensure_dir(out_dir)

    if "none-any" in in_filename:
        run(f"cp {in_filename} {out_dir}/{in_filename}")
        out_filename = abspath(f"{out_dir}/{in_filename}")
    else:
        tmp_dir = "build/fix_wheel"
        run(f"mkdir {tmp_dir}")
        run(f"unzip -q {in_filename} -d {tmp_dir}")
        log("Changing compatibility tags")
        abi_tag = "cp" + libpython_version(args).replace(".", "")
        python_tag = re.sub(r"[a-z]*$", "", abi_tag)
        platform_tag = re.sub(r"[-.]", "_", f"android_{args.api_level}_{args.abi}")
        compatibility_tag = f"{python_tag}-{abi_tag}-{platform_tag}"

        # Passing through parse_version normalizes the version, e.g. 2017.02.02 -> 2017.2.2
        dist_name = f"{args.package}-{parse_version(args.version)}"
        dist_info_dir = f"{tmp_dir}/{dist_name}.dist-info"
        EXT_SUFFIX = sysconfig.get_config_var("EXT_SUFFIX")
        for line in csv.reader(open(f"{dist_info_dir}/RECORD")):
            filename = f"{tmp_dir}/{line[0]}"
            if filename.endswith(EXT_SUFFIX):
                os.rename(filename, filename.replace(EXT_SUFFIX, ".so"))

        wheel_info = email.parser.Parser().parse(open(f"{dist_info_dir}/WHEEL"))
        del wheel_info["Tag"]
        wheel_info["Tag"] = compatibility_tag
        email.generator.Generator(open(f"{dist_info_dir}/WHEEL", "w"),
                                  maxheaderlen=0).flatten(wheel_info)

        bdist_wheel.write_record(None, tmp_dir, dist_info_dir)
        out_filename = archive_wheelfile(f"{out_dir}/{dist_name}-{compatibility_tag}", tmp_dir)
    log(f"Wrote {out_filename}")


def libpython_version(args):
    python_libs = libpython_dir(args)
    for name in os.listdir(python_libs):
        match = re.match(r"libpython(.*).so", name)
        if match:
            return match.group(1)
            break
    else:
        raise CommandError(f"Can't find libpython*.so in {python_libs}")

def libpython_dir(args):
    result = f"{args.python}/libs/{args.abi}"
    assert_isdir(result)
    return result


def run(command):
    log(command)
    try:
        subprocess.run(shlex.split(command), check=True)
    except subprocess.CalledProcessError as e:
        raise CommandError(f"Command returned exit status {e.returncode}")


def ensure_dir(dirname):
    if not exists(dirname):
        run(f"mkdir {dirname}")

def assert_isdir(filename):
    assert_exists(filename)
    if not isdir(filename):
        raise CommandError(f"{filename} is not a directory")

def assert_exists(filename):
    if not exists(filename):
        raise CommandError(f"{filename} does not exist")


def cd(new_dir):
    log(f"cd {new_dir}")
    os.chdir(new_dir)


def log(s):
    print(f"{PROGRAM_NAME}: {s}")


class CommandError(Exception):
    pass


if __name__ == "__main__":
    main()
