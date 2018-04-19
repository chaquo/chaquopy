#!/usr/bin/env python3
#
# This script was based on the following:
#   - Kivy's python-for-android, especially archs.py and recipe.py
#   - https://developer.android.com/ndk/guides/standalone_toolchain.html

# Always built as pure Python, but pure Python wheels aren't on PyPI:
#     pycparser
#
# Optionally built as pure Python, but pure Python wheels aren't on PyPI:
#     pyyaml (can use external library, and still reports itself as non-pure even when not using it)
#     MarkupSafe (self-contained)
#
# Requires external library:
#     libffi: cffi
#     libzmq: pyzml
#     openssl: cryptography, pycrypto, scrypt (OpenSSL is statically linked into the Python ssl
#         module, so to support these packages, we simply need to distribute that as a shared
#         library instead.
#
# Self-contained:
#     numpy
#     regex
#     twisted
#     ujson

import argparse
from copy import deepcopy
import csv
from email import generator, message, parser
from glob import glob
import jsonschema
import multiprocessing
import os
from os.path import abspath, basename, dirname, exists, isdir, join
import pkg_resources
import re
import shlex
import subprocess
import sys
import sysconfig
import tempfile

import attr
from wheel.archive import archive_wheelfile
from wheel.bdist_wheel import bdist_wheel
import yaml


PROGRAM_NAME = basename(__file__)
PYPI_DIR = abspath(dirname(__file__))

HOST_PLATFORM = "linux-x86_64"
GCC_VERSION = "4.9"


@attr.s
class Abi:
    name = attr.ib()
    default_api_level = attr.ib()
    toolchain = attr.ib()
    tool_prefix = attr.ib()
    cflags = attr.ib(default="")
    ldflags = attr.ib(default="")

ABIS = {abi.name: abi for abi in [
    Abi("armeabi-v7a", 15, "arm-linux-androideabi", "arm-linux-androideabi",
        cflags="-march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 -mthumb",  # See standalone
        ldflags="-march=armv7-a -Wl,--fix-cortex-a8"),                       # toolchain docs.
    Abi("x86", 15, "x86", "i686-linux-android"),
]}


class BuildWheel:

    def main(self):
        try:
            self.parse_args()
            self.package_dir = package_dir(self.package)
            assert_isdir(self.package_dir)

            self.meta = load_meta(self.package_dir)
            self.package = self.meta["package"]["name"]
            self.version = str(self.meta["package"]["version"])  # YAML may parse it as a number.
            self.find_python()

            version_dir = f"{self.package_dir}/build/{self.version}"
            ensure_dir(version_dir)
            cd(version_dir)
            self.build_dir = f"{version_dir}/{self.compat_tag}"

            if self.no_unpack:
                log("Skipping download and unpack due to --no-unpack")
                assert_isdir(self.build_dir)
            else:
                ensure_empty(self.build_dir)
                self.unpack_source()
                self.apply_patches()

            if self.no_build:
                log("Skipping build due to --no-build")
            else:
                self.update_env()
                cd(f"{self.build_dir}/src")
                wheel_filename = self.build_wheel()
                self.fix_wheel(wheel_filename)

        except CommandError as e:
            log(str(e))
            sys.exit(1)

    def parse_args(self):
        ap = argparse.ArgumentParser(add_help=False)
        ap.add_argument("--help", action="help", help=argparse.SUPPRESS)
        ap.add_argument("-v", "--verbose", action="store_true", help="Log more detail")

        skip_group = ap.add_mutually_exclusive_group()
        skip_group.add_argument("--no-unpack", action="store_true", help="Skip download and unpack "
                                "(requires source to already be unpacked in expected location)")
        skip_group.add_argument("--no-build", action="store_true", help="Download and unpack, but "
                                "skip build")

        ap.add_argument("--build-toolchain", metavar="DIR", help="Build standalone toolchain "
                        "from given NDK (optional if toolchain already exists)")
        ap.add_argument("--python", metavar="DIR", help="Path to target Python files. Required "
                        "if package contains Python code. Must follow Crystax sources/python/X.Y "
                        "layout, containing include and libs subdirectories.")
        ap.add_argument("--abi", metavar="ABI", required=True, choices=sorted(ABIS.keys()),
                        help="Choices: %(choices)s")
        ap.add_argument("--api-level", metavar="N", type=int,
                        help="Android API level (default: {})".format(
                            ", ".join(f"{abi.name}:{abi.default_api_level}"
                                      for abi in ABIS.values())))
        ap.add_argument("package")
        ap.parse_args(namespace=self)

        if not self.api_level:
            self.api_level = ABIS[self.abi].default_api_level
        self.platform_tag = f"android_{self.api_level}_{self.abi.replace('-', '_')}"

    def find_python(self):
        # For now we're assuming that non-PyPI packages don't require Python. If this ever
        # changes, we can indicate it by adding "python" as a host requirement and changing
        # build-wheel to handle that.
        self.needs_python = (self.meta["source"] == "pypi")
        if self.needs_python:
            if not self.python:
                raise CommandError("This package contains Python code: the --python option is "
                                   "required.")
            self.python_lib_dir = f"{self.python}/libs/{self.abi}"
            assert_isdir(self.python_lib_dir)
            for name in os.listdir(self.python_lib_dir):
                match = re.match(r"libpython(.*).so", name)
                if match:
                    self.python_lib_version = match.group(1)
                    self.python_version = re.sub(r"[a-z]*$", "", self.python_lib_version)

                    # We require the build and target Python versions to be the same, because
                    # many native build scripts are affected by sys.version, especially to
                    # distinguish between Python 2 and 3. To install multiple Python versions
                    # in one virtualenv, simply run mkvirtualenv again with a different -p
                    # argument.
                    self.pip = "pip" + self.python_version
                    break
            else:
                raise CommandError(f"Can't find libpython*.so in {self.python_lib_dir}")

            self.compat_tag = (f"cp{self.python_version.replace('.', '')}-"
                               f"cp{self.python_lib_version.replace('.', '')}-"
                               f"{self.platform_tag}")
        else:
            self.compat_tag = f"py2.py3-none-{self.platform_tag}"

    def unpack_source(self):
        src_dir = f"{self.build_dir}/src"
        source = self.meta["source"]
        if not source:
            ensure_dir(src_dir)
        else:
            source_filename = (self.download_pypi() if source == "pypi"
                               else self.download_url(source["url"]))
            temp_dir = tempfile.mkdtemp(prefix="build-wheel-")
            if source_filename.endswith("zip"):
                run(f"unzip -d {temp_dir} -q {source_filename}")
            else:
                run(f"tar -C {temp_dir} -xf {source_filename}")

            files = os.listdir(temp_dir)
            if len(files) == 1 and isdir(f"{temp_dir}/{files[0]}"):
                run(f"mv {temp_dir}/{files[0]} {src_dir}")
                run(f"rm -rf {temp_dir}")
            else:
                run(f"mv {temp_dir} {src_dir}")

            # This is pip's equivalent to our requirements mechanism.
            if exists(f"{src_dir}/pyproject.toml"):
                run(f"rm {src_dir}/pyproject.toml")

    def download_pypi(self):
        sdist_filename = self.find_sdist()
        if sdist_filename:
            log("Using existing source archive")
        else:
            # Even with --no-deps, pip 9.0.3 still runs egg_info on the downloaded sdist. If
            # this takes a long time, simply Ctrl-C and run build-wheel again.
            run(f"{self.pip} download{' -v' if self.verbose else ''} --no-deps "
                f"--no-binary :all: {self.package}=={self.version}")
            sdist_filename = self.find_sdist()
            if not sdist_filename:
                raise CommandError("Can't find downloaded source archive: maybe it has an "
                                   "unknown filename extension")
        return sdist_filename

    def find_sdist(self):
        for ext in ["zip", "tar.gz", "tgz", "tar.bz2", "tbz2", "tar.xz", "txz"]:
            filename = f"{self.package}-{self.version}.{ext}"
            if exists(filename):
                return filename

    def download_url(self, url):
        source_filename = url[url.rfind("/") + 1:]
        if exists(source_filename):
            log("Using existing source archive")
        else:
            run(f"wget {url}")
        return source_filename

    def apply_patches(self):
        patches_dir = f"{self.package_dir}/patches"
        if exists(patches_dir):
            cd(f"{self.build_dir}/src")
            for patch_filename in os.listdir(patches_dir):
                run(f"patch -t -p1 -i {patches_dir}/{patch_filename}")

    def build_wheel(self):
        self.extract_requirements()
        build_script = f"{self.package_dir}/build.sh"
        if exists(build_script):
            return self.build_with_script(build_script)
        else:
            return self.build_with_pip()  # Assume it's a Python source tree.

    def extract_requirements(self):
        reqs = self.host_requirements()
        if not reqs:
            return

        reqs_dir = f"{self.build_dir}/requirements"
        ensure_empty(reqs_dir)
        for package, version in reqs:
            wheel_prefix = (f"{package_dir(package)}/dist/{normalize_name_wheel(package)}-"
                            f"{normalize_version(version)}-*")  # '*' matches the build tag.
            wheel_filename = None
            for compat_tag in [self.compat_tag, f"py2.py3-none-{self.platform_tag}"]:
                pattern = f"{wheel_prefix}-{compat_tag}.whl"
                wheels = glob(pattern)
                if len(wheels) == 1:
                    wheel_filename = wheels[0]
                    break
                elif len(wheels) > 1:
                    raise CommandError(f"Found multiple wheels matching {pattern}: please remove "
                                       f"the ones you don't want to use.")
            if not wheel_filename:
                raise CommandError(f"Couldn't find requirement {package} {version}")
            run(f"unzip -d {reqs_dir} -q {wheel_filename}")

    def build_with_script(self, build_script):
        prefix_dir = f"{self.build_dir}/prefix"
        ensure_empty(f"{prefix_dir}/chaquopy")
        os.environ.update({  # Use CHAQUOPY prefix for variables not used by conda.
            "CHAQUOPY_ABI": self.abi,
            "CPU_COUNT": str(multiprocessing.cpu_count()),
            "RECIPE_DIR": self.package_dir,
            "SRC_DIR": os.getcwd(),
            "PREFIX": f"{prefix_dir}/chaquopy",
        })
        run(build_script)

        info_dir = f"{prefix_dir}/{self.package}-{self.version}.dist-info"
        ensure_dir(info_dir)

        info_wheel = message.Message()
        update_message(info_wheel, {"Wheel-Version": "1.0",
                                    "Root-Is-Purelib": "false"})
        write_message(info_wheel, f"{info_dir}/WHEEL")

        info_metadata = message.Message()
        update_message(info_metadata, {"Metadata-Version": "1.2",
                                       "Name": self.package,
                                       "Version": self.version,
                                       "Summary": "",        # Compulsory according to PEP 345,
                                       "Download-URL": ""})  #
        write_message(info_metadata, f"{info_dir}/METADATA")

        return self.package_wheel(prefix_dir, os.getcwd())

    def build_with_pip(self):
        # We can't run "setup.py bdist_wheel" directly, because that would only work with
        # setuptools-aware setup.py files.
        run(f"{self.pip} wheel{' -v' if self.verbose else ''} --no-deps "
            f"--no-clean --build-option --keep-temp "  # Makes diagnosing problems easier
            f"--build-option --universal "
            f"-e .")
        wheel_filename, = glob("*.whl")  # Note comma
        return abspath(wheel_filename)

    # The environment variables set in this function are used for native builds by
    # distutils.sysconfig.customize_compiler. To make builds as consistent as possible, we
    # define values for all the overridable variables, but some are not overridable in Python
    # 3.6 (e.g. OPT). We also define some common variables like LD and STRIP which aren't used
    # by distutils, but might be used by custom build scripts.
    def update_env(self):
        env = {}
        abi = ABIS[self.abi]
        toolchain_dir = self.get_toolchain(abi)
        for tool in ["ar", "as", ("cc", "gcc"), "cpp", ("cxx", "g++"),
                     ("fc", "gfortran"),   # Used by openblas
                     ("f90", "gfortran"),  # Used by numpy.distutils
                     "ld", "nm", "ranlib", "readelf", "strip"]:
            var, suffix = (tool, tool) if isinstance(tool, str) else tool
            filename = f"{toolchain_dir}/bin/{abi.tool_prefix}-{suffix}"
            assert_exists(filename)
            env[var.upper()] = filename

        env["CFLAGS"] = (  # Will be added to CC and LDSHARED commands.
            f"-fPIC "  # See standalone toolchain docs, and note below about -pie
            f"-Werror=implicit-function-declaration "  # Many libc symbols are missing on old API
            f"{abi.cflags}")                           #   levels: using one should be an error.
        env["LDSHARED"] = f"{env['CC']} -shared"

        # Not including -pie despite recommendation in standalone toolchain docs, because it
        # causes the linker to forget it's supposed to be building a shared library
        # (https://lists.debian.org/debian-devel/2016/05/msg00302.html)
        env["LDFLAGS"] = (  # Will be added to LDSHARED commands.
            f"-lm "  # Many packages get away with omitting this on standard Linux.
            f"-Wl,--no-undefined "  # Many libc symbols are missing on old API levels: using
            f"{abi.ldflags}")       #   does a similar thing for the linker.

        env["ARFLAGS"] = "rc"

        # Set all unused overridable variables to the empty string to prevent the host Python
        # values (if any) from taking effect.
        for var in ["CPPFLAGS", "CXXFLAGS"]:
            assert var not in env, var
            env[var] = ""

        if self.needs_python:
            # TODO: distutils adds -I arguments for the build Python's include directory (and
            # virtualenv include directory if applicable). They're at the end of the command
            # line so they should be overridden, but may still cause problems if they happen to
            # have a header which isn't present in the target Python include directory. The
            # only way I can see to avoid this is to set CC to a wrapper script.
            ipython = f"{self.python}/include/python"
            assert_isdir(ipython)
            env["CFLAGS"] += f" -I{ipython}"
            env["LDFLAGS"] += f" -L{self.python_lib_dir} -lpython{self.python_lib_version}"

        if self.verbose:
            log("Environment set as follows:\n" +
                "\n".join(f"export {name}='{env[name]}'" for name in sorted(env.keys())))
        os.environ.update(env)

    def get_toolchain(self, abi):
        toolchain_dir = f"{PYPI_DIR}/toolchains/{self.platform_tag}"
        if self.build_toolchain:
            if exists(toolchain_dir):
                log(f"Rebuilding toolchain {self.platform_tag}")
                run(f"rm -rf {toolchain_dir}")
            else:
                log(f"Building new toolchain {self.platform_tag}")
            run(f"{self.build_toolchain}/build/tools/make-standalone-toolchain.sh "
                f"--toolchain={abi.toolchain}-{GCC_VERSION} "
                f"--platform=android-{self.api_level} "
                f"--install-dir={toolchain_dir}")

            # The Crystax make-standalone-toolchain.sh renames libgnustl_static.a to
            # libstdc++.a, but leaves libgnustl_shared.so at its original name. This would lead
            # us to link against the static library by default, which is unsafe for the reasons
            # given at https://developer.android.com/ndk/guides/cpp-support.html. So we'll
            # rename the shared library as well. (Its SONAME is still libgnustl_shared.so, so
            # that's the filename expected at runtime.)
            lib_dir = f"{toolchain_dir}/{abi.tool_prefix}/lib"
            run(f"mv {lib_dir}/libgnustl_shared.so {lib_dir}/libstdc++.so")

        else:
            if exists(toolchain_dir):
                log(f"Using existing toolchain {self.platform_tag}")
            else:
                raise CommandError(f"No existing toolchain for {self.platform_tag}: "
                                   f"pass --build-toolchain to build it.")

        return toolchain_dir

    def fix_wheel(self, in_filename):
        if "py2.py3-none-any" in in_filename:
            is_pure = True
            self.compat_tag = "py2.py3-none-any"
        else:
            is_pure = False

        tmp_dir = f"{self.build_dir}/fix_wheel"
        ensure_empty(tmp_dir)
        cd(tmp_dir)
        run(f"unzip -q {in_filename}")
        info_dir, = glob("*.dist-info")  # Note comma

        log("Updating WHEEL file")
        info_wheel = read_message(f"{info_dir}/WHEEL")
        update_message(info_wheel, {"Generator": PROGRAM_NAME,
                                    "Build": str(self.meta["build"]["number"]),
                                    "Tag": expand_compat_tag(self.compat_tag)})
        write_message(info_wheel, f"{info_dir}/WHEEL")

        if not is_pure:
            log("Processing native libraries")
            host_soabi = sysconfig.get_config_var("SOABI")
            for original_path, _, _ in csv.reader(open(f"{info_dir}/RECORD")):
                if re.search(r"\.(so(\..*)?|a)$", original_path):
                    # On Python 3, native modules will be tagged with the build platform, e.g.
                    # `foo.cpython-36m-x86_64-linux-gnu.so`. Remove these tags.
                    fixed_path = re.sub(fr"\.{host_soabi}\.so$", ".so", original_path)
                    if fixed_path != original_path:
                        run(f"mv {original_path} {fixed_path}")

                    # https://www.technovelty.org/linux/stripping-shared-libraries.html
                    run(f"{os.environ['STRIP']} --strip-unneeded {fixed_path}")

        reqs = self.host_requirements()
        if reqs:
            log("Adding extra requirements")
            info_metadata = read_message(f"{info_dir}/METADATA")
            update_message(info_metadata, {"Requires-Dist": [f"{package} (>={version})"
                                                             for package, version in reqs]},
                           replace=False)
            write_message(info_metadata, f"{info_dir}/METADATA")

            # Remove the JSON copy to save us from having to update it too.
            info_metadata_json = f"{info_dir}/metadata.json"
            if exists(info_metadata_json):
                run(f"rm {info_metadata_json}")

        out_dir = f"{self.package_dir}/dist"
        ensure_dir(out_dir)
        out_filename = self.package_wheel(tmp_dir, out_dir)
        log(f"Wrote {out_filename}")

    def package_wheel(self, in_dir, out_dir):
        info_dir, = glob(f"{in_dir}/*.dist-info")  # Note comma
        bdist_wheel.write_record(None, in_dir, info_dir)
        return archive_wheelfile(
            "-".join([
                f"{out_dir}/{normalize_name_wheel(self.package)}",
                normalize_version(self.version),
                str(self.meta["build"]["number"]),
                self.compat_tag]),
            in_dir)

    def host_requirements(self):
        reqs = []
        for req in self.meta["requirements"]["host"]:
            package, version = req.split()
            package = load_meta(package)["package"]["name"]
            reqs.append((package, version))
        return reqs


def read_message(filename):
    return parser.Parser().parse(open(filename))

def update_message(msg, d, replace=True):
    for key, values in d.items():
        if replace:
            del msg[key]  # Removes all lines with this key.
        if not isinstance(values, list):
            values = [values]
        for value in values:
            # __setitem__ doesn't overwrite existing lines here.
            msg[key] = value

def write_message(msg, filename):
    # I don't know whether maxheaderlen is required, but it's used by bdist_wheel.
    generator.Generator(open(filename, "w"), maxheaderlen=0).flatten(msg)


def load_meta(package):
    # http://python-jsonschema.readthedocs.io/en/latest/faq/
    def with_defaults(validator_cls):
        def set_defaults(validator, properties, instance, schema):
            for name, subschema in properties.items():
                if "default" in subschema:
                    instance.setdefault(name, deepcopy(subschema["default"]))
            yield from validator_cls.VALIDATORS["properties"](
                validator, properties, instance, schema)

        return jsonschema.validators.extend(validator_cls, {"properties": set_defaults})

    # Work around https://github.com/Julian/jsonschema/issues/367 by not enabling defaults
    # during meta-schema validation.
    Validator = jsonschema.Draft4Validator
    schema = yaml.safe_load(open(f"{PYPI_DIR}/meta-schema.yaml"))
    Validator.check_schema(schema)
    meta = yaml.safe_load(open(f"{package_dir(package)}/meta.yaml"))
    with_defaults(Validator)(schema).validate(meta)
    return meta


def package_dir(package):
    return join(PYPI_DIR, "packages", normalize_name_pypi(package))


# See PEP 503.
def normalize_name_pypi(name):
    return re.sub(r"[-_.]+", "-", name).lower()

# See PEP 427.
def normalize_name_wheel(name):
    return re.sub(r"[-_.]+", "_", name)

#  e.g. "2017.01.02" -> "2017.1.2"
def normalize_version(version):
    return str(pkg_resources.parse_version(version))


def expand_compat_tag(compat_tag):
    result = []
    impl_tags, abi_tags, plat_tags = compat_tag.split("-")
    for impl in impl_tags.split('.'):
        for abi in abi_tags.split('.'):
            for plat in plat_tags.split('.'):
                result.append('-'.join((impl, abi, plat)))
    return result


def run(command):
    log(command)
    try:
        subprocess.run(shlex.split(command), check=True)
    except subprocess.CalledProcessError as e:
        raise CommandError(f"Command returned exit status {e.returncode}")


def ensure_empty(dir_name):
    if exists(dir_name):
        run(f"rm -rf {dir_name}")
    ensure_dir(dir_name)

def ensure_dir(dir_name):
    if not exists(dir_name):
        run(f"mkdir -p {dir_name}")

def assert_isdir(filename):
    assert_exists(filename)
    if not isdir(filename):
        raise CommandError(f"{filename} is not a directory")

def assert_exists(filename):
    if not exists(filename):
        raise CommandError(f"{filename} does not exist")


def cd(new_dir):
    if new_dir != os.getcwd():
        log(f"cd {new_dir}")
        os.chdir(new_dir)


def log(s):
    print(f"{PROGRAM_NAME}: {s}")


class CommandError(Exception):
    pass


if __name__ == "__main__":
    BuildWheel().main()
