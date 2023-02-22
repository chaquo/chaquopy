#!/usr/bin/env python3

from abc import abstractmethod
import argparse
from copy import deepcopy
import csv
from dataclasses import dataclass, field
from email import generator, message, parser
from glob import glob
import jsonschema
import multiprocessing
import os
from os.path import abspath, basename, dirname, exists, isdir, join
import pkg_resources
import re
from setuptools._distutils.util import split_quoted
import shlex
import subprocess
import sys
import tempfile
from textwrap import dedent

# from elftools.elf.elffile import ELFFile
import jinja2
import yaml


PROGRAM_NAME = basename(__file__)
PYPI_DIR = abspath(dirname(__file__))
RECIPES_DIR = f"{PYPI_DIR}/packages"

# Libraries are grouped by minimum API level and listed under their SONAMEs.
STANDARD_LIBS = [
    # Android native APIs (https://developer.android.com/ndk/guides/stable_apis)
    (16, ["libandroid.so", "libc.so", "libdl.so", "libEGL.so", "libGLESv1_CM.so", "libGLESv2.so",
          "libjnigraphics.so", "liblog.so", "libm.so", "libOpenMAXAL.so", "libOpenSLES.so",
          "libz.so"]),
    (21, ["libmediandk.so"]),

    # Chaquopy-provided libraries
    (0, ["libcrypto_chaquopy.so", "libsqlite3_chaquopy.so", "libssl_chaquopy.so"]),
]

# Not including chaquopy-libgfortran: the few packages which require it must specify it in
# meta.yaml. That way its location will always be passed to the linker with an -L flag, and we
# won't need to worry about the multilib subdirectory structure of the armeabi-v7a toolchain.
#
# TODO: break out the build script fragments which get the actual version numbers from the
# toolchain, and call them here.
COMPILER_LIBS = {
    "libc++_shared.so": ("chaquopy-libcxx", "10000"),
    "libomp.so": ("chaquopy-libomp", "9.0.9"),
}



@dataclass
class Abi:
    name: str                               # Android ABI name.
    tool_prefix: str                        # GCC target triplet.
    cflags: str = field(default="")
    ldflags: str = field(default="")
    sdk: str = field(default="")
    slice: str = field(default="")

# If any flags are changed, consider also updating target/build-common-tools.sh.
# The ABIS dictionary is layered: os->sdk->architecture.
ABIS = {
    'android': {
        'android': {
            abi.name: abi for abi in [
                Abi("armeabi-v7a", "arm-linux-androideabi",
                    cflags="-march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 -mthumb",  # See standalone
                    ldflags="-march=armv7-a -Wl,--fix-cortex-a8"),                       # toolchain docs.
                Abi("arm64-v8a", "aarch64-linux-android"),
                Abi("x86", "i686-linux-android"),
                Abi("x86_64", "x86_64-linux-android"),
            ]
        }
    },
    'iOS': {
        'iphoneos': {
            'arm64': Abi("iphoneos_arm64", "arm64-apple-ios", sdk="iphoneos", slice="ios-arm64"),
        },
        'iphonesimulator': {
            'arm64': Abi("iphonesimulator_arm64", "arm64-apple-ios-simulator", sdk="iphonesimulator", slice="ios-arm64_x86_64-simulator"),
            'x86_64': Abi("iphonesimulator_x86_64", "x86_64-apple-ios-simulator", sdk="iphonesimulator", slice="ios-arm64_x86_64-simulator")
        }
    },
    'tvOS': {
        'appletvos': {
            'arm64': Abi("appletvos_arm64", "arm64-apple-tvos", sdk="appletvos", slice="tvos-arm64"),
        },
        'appletvsimulator': {
            'arm64': Abi("appletvsimulator_arm64", "arm64-apple-tvos-simulator", sdk="appletvsimulator", slice="tvos-arm64_x86_64-simulator"),
            'x86_64': Abi("appletvsimulator_x86_64", "x86_64-apple-tvos-simulator", sdk="appletvsimulator", slice="tvos-arm64_x86_64-simulator")
        }
    },
    'watchOS': {
        'watchos': {
            'arm64_32': Abi("watchos_arm64_32", "arm64_32-apple-watchos", sdk="watchos", slice="watchos-arm64_32"),
        },
        'watchsimulator': {
            'arm64': Abi("watchsimulator_arm64", "arm64-apple-watchos-simulator", sdk="watchsimulator", slice="watchos-arm64_x86_64-simulator"),
            'x86_64': Abi("watchsimulator_x86_64", "x86_64-apple-watchos-simulator", sdk="watchsimulator", slice="watchos-arm64_x86_64-simulator")
        }
    }
}


class Package:
    def __init__(self, package_name_or_recipe, package_version, build_number):
        self.recipe_dir = self.find_package(package_name_or_recipe)
        self.meta = self.load_meta(self.recipe_dir, override_version=package_version, override_build=build_number)
        self.name = self.meta["package"]["name"]
        self.version = self.meta["package"]["version"]

        self.version_dir = f"{self.recipe_dir}/build/{self.version}"

        self.name_version = normalize_name_wheel(self.name) + "-" + normalize_version(self.version)

        # Determine if the build needs Python
        self.needs_python = (self.meta["source"] == "pypi")

        # Determine if the build needs CMake
        self.needs_cmake = False
        if "cmake" in self.meta["requirements"]["build"]:
            self.meta["requirements"]["build"].remove("cmake")
            self.needs_cmake = True

        # Gather any additional bundled requirements
        self.bundled_reqs = []
        for name in ["openssl", "python", "sqlite"]:
            if name in self.meta["requirements"]["host"]:
                self.meta["requirements"]["host"].remove(name)
                if name == "python":
                    self.needs_python = True
                else:
                    # OpenSSL and SQLite currently work without any build flags, but it's
                    # worth keeping them in existing meta.yaml files in case that changes.
                    self.bundled_reqs.append(name)

    def find_package(self, name):
        if "/" in name:
            package_dir = abspath(name)
        else:
            package_dir = join(RECIPES_DIR, normalize_name_pypi(name))
        assert_isdir(package_dir)
        return package_dir

    def load_meta(self, package_dir, override_version, override_build):
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

        with open(f"{package_dir}/meta.yaml") as f:
            meta_template = f.read()
            if override_version:
                # If there's an override version, look for any {% set version... %}
                # content in the template, and ensure it is replaced with the
                # override version.
                meta_template = re.sub(
                    r'{% set version = ".*?" %}',
                    f'{{% set version = "{override_version}" %}}',
                    meta_template
                )

        # Render the meta template.
        meta_str = jinja2.Template(meta_template).render()

        # Parse the rendered meta template
        meta = yaml.safe_load(meta_str)

        # If there's a version override, set it in the package metadata;
        # if there's a build number override, set it; otherwise purge
        # the build number (since it won't match the override version)
        if override_version:
            try:
                meta["package"]["version"] = override_version
                if override_build:
                    meta.setdefault("build", {})["number"] = override_build
                else:
                    del meta["build"]["number"]
            except KeyError:
                pass

        with_defaults(Validator)(schema).validate(meta)
        return meta


class BaseWheelBuilder:
    def __init__(self, package, toolchain, python_version, abi, api_level, standard_libs, verbose, no_unpack, no_build, no_reqs):
        # Properties describing the package that will be built
        self.package = package
        self.toolchain = toolchain
        self.python_version = python_version
        self.abi = abi
        self.api_level = api_level
        self.standard_libs = standard_libs

        # Verbosity and other build options
        self.verbose = verbose
        self.no_unpack = no_unpack
        self.no_build = no_build
        self.no_reqs = no_reqs

        # Properties that should be overwritten by subclasses
        self.os = "UNKNOWN"
    @property
    def python_version_tag(self):
        return self.python_version.replace('.', '')

    @property
    def platform_tag(self):
        return f"{self.os.lower()}_{self.api_level.replace('.','_')}_{self.abi.name}"

    @property
    def non_python_compat_tag(self):
        return f"py3-none-{self.platform_tag}"

    def build(self):
        if self.package.needs_python:
            self.find_python()
            self.pip = f"python{self.python_version} -m pip --disable-pip-version-check"
            self.compat_tag = (
                f"cp{self.python_version_tag}-"
                f"cp{self.python_version_tag}-"
                f"{self.platform_tag}"
            )
        else:
            self.compat_tag = self.non_python_compat_tag

        build_reqs = self.get_requirements("build")
        if build_reqs:
            run(f"{self.pip} install{' -v' if self.verbose else ''} " +
                " ".join(f"{name}=={version}" for name, version in build_reqs))

        ensure_dir(self.package.version_dir)
        cd(self.package.version_dir)
        self.build_dir = f"{self.package.version_dir}/{self.compat_tag}"
        self.src_dir = f"{self.build_dir}/src"

        if self.no_unpack:
            log("Skipping download and unpack due to --no-unpack")
            assert_isdir(self.build_dir)
        else:
            ensure_empty(self.build_dir)
            self.unpack_source()
            self.apply_patches()

        if self.no_build:
            log("Skipping build due to --no-build")
            return []
        else:
            self.reqs_dir = f"{self.build_dir}/requirements"
            if self.no_reqs:
                log("Skipping requirements extraction due to --no-reqs")
            else:
                self.extract_requirements()
            self.update_env()
            wheel_filename = self.fix_wheel(self.build_wheel())
            self.reset_env()
            return wheel_filename

    def find_python(self):
        if self.python_version is None:
            raise CommandError("This package requires Python: specify a version number "
                               "with the --python argument")

        # Check version number format.
        ERROR = CommandError("--python version must be in the form X.Y, where X and Y "
                             "are both numbers")
        components = self.python_version.split(".")
        if len(components) != 2:
            raise ERROR
        for c in components:
            try:
                int(c)
            except ValueError:
                raise ERROR

    def unpack_source(self):
        source = self.package.meta["source"]
        if not source:
            ensure_dir(self.src_dir)
        elif "path" in source:
            abs_path = abspath(join(self.package.recipe_dir, source["path"]))
            run(f"cp -a {abs_path} {self.src_dir}")
        else:
            source_filename = (self.download_git(source) if "git_url" in source
                               else self.download_pypi() if source == "pypi"
                               else self.download_url(source["url"]))
            temp_dir = tempfile.mkdtemp(prefix="build-wheel-")
            if source_filename.endswith("zip"):
                run(f"unzip -d {temp_dir} -q {source_filename}")
            else:
                run(f"tar -C {temp_dir} -xf {source_filename}")

            files = os.listdir(temp_dir)
            if len(files) == 1 and isdir(f"{temp_dir}/{files[0]}"):
                run(f"mv {temp_dir}/{files[0]} {self.src_dir}")
                run(f"rm -rf {temp_dir}")
            else:
                run(f"mv {temp_dir} {self.src_dir}")

            # pyproject.toml may conflict with our own requirements mechanism, so we currently
            # disable it.
            if exists(f"{self.src_dir}/pyproject.toml"):
                run(f"mv {self.src_dir}/pyproject.toml "
                    f"{self.src_dir}/pyproject-chaquopy-disabled.toml")

    def download_git(self, source):
        git_rev = source["git_rev"]
        is_hash = len(str(git_rev)) == 40

        # Clones with many submodules can be slow, so cache the clean repository tree.
        tgz_filename = f"{self.package.name}-{git_rev}.tar.gz"
        if exists(tgz_filename):
            log("Using cached repository")
        else:
            clone_cmd = "git clone --recurse-submodules"
            if not is_hash:
                # Unfortunately --depth doesn't apply to submodules, and --shallow-submodules
                # doesn't work either (https://github.com/rust-lang/rust/issues/34228).
                clone_cmd += f" -b {git_rev} --depth 1 "
            temp_dir = tempfile.mkdtemp(prefix="build-wheel-")
            run(f"{clone_cmd} {source['git_url']} {temp_dir}")
            if is_hash:
                run(f"git -C {temp_dir} checkout --detach {git_rev}")
                run(f"git -C {temp_dir} submodule update --init")

            run(f"tar -zcf {tgz_filename} -C {temp_dir} .")
            run(f"rm -rf {temp_dir}")

        return tgz_filename

    def download_pypi(self):
        sdist_filename = self.find_sdist()
        if sdist_filename:
            log("Using cached sdist")
        else:
            result = run(f"{self.pip} download{' -v' if self.verbose else ''} --no-deps "
                         f"--no-binary {self.package.name} --no-build-isolation "
                         f"{self.package.name}=={self.package.version}", check=False)
            if result.returncode:
                # Even with --no-deps, `pip download` still pointlessly runs egg_info on the
                # downloaded sdist, which installs anything in `setup_requires`
                # (https://github.com/pypa/pip/issues/1884). If this fails or takes a long
                # time, we can't work around it by patching the package, because we haven't had
                # a chance to apply the patches yet.
                warn(f"pip download returned exit status {result.returncode}")
            sdist_filename = self.find_sdist()
            if not sdist_filename:
                raise CommandError("Can't find downloaded source archive. Does the name and "
                                   "version in the package's meta.yaml match the filename "
                                   "shown above?")
        return sdist_filename

    def find_sdist(self):
        for ext in ["zip", "tar.gz", "tgz", "tar.bz2", "tbz2", "tar.xz", "txz"]:
            filename = f"{self.package.name}-{self.package.version}.{ext}"
            if exists(filename):
                return filename

    def download_url(self, url):
        source_filename = url[url.rfind("/") + 1:]
        if exists(source_filename):
            log("Using cached source archive")
        else:
            run(f"wget {url}")
        return source_filename

    def apply_patches(self):
        base_patches_dir = f"{self.package.recipe_dir}/patches"
        if exists(base_patches_dir):
            cd(self.src_dir)
            for patch_filename in os.listdir(base_patches_dir):
                if not os.path.isdir(f"{base_patches_dir}/{patch_filename}"):
                    run(f"patch -p1 -i {base_patches_dir}/{patch_filename}")

        patches_dir = f"{base_patches_dir}/{self.os}"
        if exists(patches_dir):
            cd(self.src_dir)
            for patch_filename in os.listdir(patches_dir):
                run(f"patch -p1 -i {patches_dir}/{patch_filename}")

    def build_wheel(self):
        cd(self.src_dir)
        build_script = f"{self.package.recipe_dir}/build.sh"
        if exists(build_script):
            return self.build_with_script(build_script)
        elif self.package.needs_python:
            return self.build_with_pip()
        else:
            raise CommandError("Don't know how to build: no build.sh exists, and this is not "
                               "declared as a Python package. Do you need to add a `host` "
                               "requirement of `python`? See meta-schema.yaml.")

    def extract_requirements(self):
        ensure_empty(self.reqs_dir)
        reqs = self.get_requirements("host")
        if not reqs:
            return

        for package, version in reqs:
            dist_dir = f"{PYPI_DIR}/dist/{normalize_name_pypi(package)}"
            matches = []
            if exists(dist_dir):
                for filename in os.listdir(dist_dir):
                    match = re.search(fr"^{normalize_name_wheel(package)}-"
                                      fr"{normalize_version(version)}-(?P<build_num>\d+)-"
                                      fr"({self.compat_tag}|"
                                      fr"{self.non_python_compat_tag})"
                                      fr"\.whl$", filename)
                    if match:
                        matches.append(match)
            if not matches:
                raise CommandError(f"Couldn't find wheel for requirement {package} {version}")
            matches.sort(key=lambda match: int(match.group("build_num")))
            wheel_filename = join(dist_dir, matches[-1].group(0))
            run(f"unzip -d {self.reqs_dir} -q {wheel_filename}")

            # Move data files into place (used by torchvision to build against torch).
            data_dir = f"{self.reqs_dir}/{package}-{version}.data/data"
            if exists(data_dir):
                for name in os.listdir(data_dir):
                    run(f"mv {data_dir}/{name} {self.reqs_dir}")

            # Put headers on the include path (used by gevent to build against greenlet).
            include_src = f"{self.reqs_dir}/{package}-{version}.data/headers"
            if exists(include_src):
                include_tgt = f"{self.reqs_dir}/opt/include/{package}"
                run(f"mkdir -p {dirname(include_tgt)}")
                run(f"mv {include_src} {include_tgt}")

        # There is an extension to allow ZIP files to contain symlnks, but the zipfile module
        # doesn't support it, and the links wouldn't survive on Windows anyway. So our library
        # wheels include external shared libraries only under their SONAMEs, and we need to
        # create links from the other names so the compiler can find them.
        SONAME_PATTERNS = [(r"^(lib.*)\.so\..*$", r"\1.so"),
                           (r"^(lib.*?)\d+\.so$", r"\1.so"),  # e.g. libpng
                           (r"^(lib.*)_chaquopy\.so$", r"\1.so")]  # e.g. libjpeg
        reqs_lib_dir = f"{self.reqs_dir}/opt/lib"
        if exists(reqs_lib_dir):
            for filename in os.listdir(reqs_lib_dir):
                for pattern, repl in SONAME_PATTERNS:
                    link_filename = re.sub(pattern, repl, filename)
                    if link_filename in self.standard_libs:
                        continue  # e.g. torch has libc10.so, which would become libc.so.
                    if link_filename != filename:
                        run(f"ln -s {filename} {reqs_lib_dir}/{link_filename}")

    def build_with_script(self, build_script):
        prefix_dir = f"{self.build_dir}/prefix"
        ensure_empty(prefix_dir)
        os.environ["PREFIX"] = ensure_dir(f"{prefix_dir}/opt")  # Conda variable name
        run(build_script)
        return package_wheel(self.package, self.compat_tag, prefix_dir, self.src_dir)

    def build_with_pip(self):
        # We can't run "setup.py bdist_wheel" directly, because that would only work with
        # setuptools-aware setup.py files. We pass -v unconditionally, because we always want
        # to see the build process output.
        run(f"{self.pip} wheel -v --no-deps "
            # --no-clean doesn't currently work: see build-packages/sitecustomize.py
            f"--no-clean --build-option --keep-temp "
            f"-e .")
        wheel_filename, = glob("*.whl")  # Note comma
        return abspath(wheel_filename)

    # The environment variables set in this function are used for native builds by
    # distutils.sysconfig.customize_compiler. To make builds as consistent as possible, we
    # define values for all environment variables used by distutils in any supported Python
    # version. We also define some common variables like LD and STRIP which aren't used
    # by distutils, but might be used by custom build scripts.
    def update_env(self):
        env = {}

        # Adding reqs_dir to PYTHONPATH allows setup.py to import requirements, for example to
        # call numpy.get_include().
        pythonpath = [f"{PYPI_DIR}/env/lib/python", self.reqs_dir]
        if "PYTHONPATH" in os.environ:
            pythonpath.append(os.environ["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath)

        self.platform_update_env(env)

        env.update({  # Conda variable names, except those starting with CHAQUOPY.
            "CHAQUOPY_ABI": self.abi.name,
            "CHAQUOPY_TRIPLET": self.abi.tool_prefix,
            "CPU_COUNT": str(multiprocessing.cpu_count()),
            "PKG_BUILDNUM": str(self.package.meta["build"]["number"]),
            "PKG_NAME": self.package.name,
            "PKG_VERSION": self.package.version,
            "RECIPE_DIR": self.package.recipe_dir,
            "SRC_DIR": self.src_dir,
        })

        for var in self.package.meta["build"]["script_env"]:
            key, value = var.split("=")
            env[key] = value

        if self.verbose:
            # Format variables so they can be pasted into a shell when troubleshooting.
            log("Environment set as follows:\n" +
                "\n".join(f"export {key}='{value}'" for key, value in env.items()))

        # Preserve a copy of all the environment variables that we're
        # about to update. Store a value of None if the key doesn't
        # exist in the base environment.
        self.orig_env = {
            key: os.environ.get(key)
            for key in env
        }
        os.environ.update(env)

        if self.package.needs_cmake:
            self.generate_cmake_toolchain()

    def reset_env(self):
        # Delete any key that didn't exist in the original environment.
        # Reset any value that did exist.
        for k, v in self.orig_env.items():
            if v is None:
                del os.environ[k]
            else:
                os.environ[k] = v

    # Define the minimum necessary to keep CMake happy. To avoid duplication, we still want to
    # configure as much as possible via update_env.
    def generate_cmake_toolchain(self):
        # See build/cmake/android.toolchain.cmake in the NDK.
        CMAKE_PROCESSORS = {
            "armeabi-v7a": "armv7-a",
            "arm64-v8a": "aarch64",
            "x86": "i686",
            "x86_64": "x86_64",
            "iphonesimulator_x86_64": "x86_64",
            "appletvsimulator_x86_64": "x86_64",
            "watchsimulator_x86_64": "x86_64",
            "iphonesimulator_arm64": "arm64",
            "appletvsimulator_arm64": "arm64",
            "watchsimulator_arm64": "arm64",
            "iphoneos_arm64": "arm64",
            "appletvos_arm64": "arm64",
            "watchos_arm64": "arm64",
        }
        clang_target = f"{self.abi.tool_prefix}{self.api_level}".replace("arm-", "armv7a-")

        toolchain_filename = join(self.build_dir, "chaquopy.toolchain.cmake")
        log(f"Generating {toolchain_filename}")
        with open(toolchain_filename, "w") as toolchain_file:
            print(dedent(f"""\
                set(ANDROID TRUE)
                set(CMAKE_ANDROID_STANDALONE_TOOLCHAIN {self.toolchain})
                set(CMAKE_SYSTEM_NAME Android)

                set(CMAKE_SYSTEM_VERSION {self.api_level})
                set(ANDROID_PLATFORM_LEVEL {self.api_level})
                set(ANDROID_NATIVE_API_LEVEL {self.api_level})  # Deprecated, but used by llvm.

                set(ANDROID_ABI {self.abi.name})
                set(CMAKE_SYSTEM_PROCESSOR {CMAKE_PROCESSORS[self.abi.name]})

                # cmake 3.16.3 defaults to passing a target containing "none", which isn't
                # recognized by NDK r19.
                set(CMAKE_C_COMPILER_TARGET {clang_target})
                set(CMAKE_CXX_COMPILER_TARGET {clang_target})

                # Our requirements dir comes before the sysroot, because the sysroot include
                # directory contains headers for third-party libraries like libjpeg which may
                # be of different versions to what we want to use.
                set(CMAKE_FIND_ROOT_PATH {self.reqs_dir}/opt {self.toolchain}/sysroot)
                set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
                set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
                set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
                set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
                """), file=toolchain_file)

            if self.package.needs_python:
                print(dedent(f"""\
                    # See https://cmake.org/cmake/help/latest/module/FindPythonLibs.html .
                    # For maximum compatibility, we set both the input and the output variables.
                    SET(PYTHONLIBS_FOUND TRUE)
                    SET(PYTHON_LIBRARY {self.python_lib})
                    SET(PYTHON_LIBRARIES {self.python_lib})
                    SET(PYTHON_INCLUDE_DIR {self.python_include_dir})
                    SET(PYTHON_INCLUDE_DIRS {self.python_include_dir})
                    SET(PYTHON_INCLUDE_PATH {self.python_include_dir})

                    # pybind11's FindPythonLibsNew.cmake has some extra variables.
                    SET(PYTHON_MODULE_EXTENSION .so)
                    """), file=toolchain_file)

    @abstractmethod
    def process_native_binaries(self, tmp_dir, info_dir):
        ...

    @abstractmethod
    def update_requirements(self, filename, reqs):
        ...

    def fix_wheel(self, in_filename):
        tmp_dir = f"{self.build_dir}/fix_wheel"
        ensure_empty(tmp_dir)
        run(f"unzip -d {tmp_dir} -q {in_filename}")
        info_dir = f"{tmp_dir}/{self.package.name_version}.dist-info"

        # Add any extra license files in the recipe dir, or referenced
        # by the meta.yaml file.
        license_files = find_license_files(self.package.recipe_dir)
        meta_license = self.package.meta["about"]["license_file"]
        if meta_license:
            license_files += [f"{self.src_dir}/{meta_license}"]
        if license_files:
            for name in license_files:
                # We use `-a` because pandas comes with a whole directory of licenses.
                run(f"cp -a {name} {info_dir}")

        reqs = self.process_native_binaries(tmp_dir, info_dir)

        reqs.update(self.get_requirements("host"))
        if reqs:
            self.update_requirements(f"{info_dir}/METADATA", reqs)
            # Remove the optional JSON copy to save us from having to update it too.
            info_metadata_json = f"{info_dir}/metadata.json"
            if exists(info_metadata_json):
                run(f"rm {info_metadata_json}")

        out_dir = ensure_dir(f"{PYPI_DIR}/dist/{normalize_name_pypi(self.package.name)}")
        out_filename = package_wheel(self.package, self.compat_tag, tmp_dir, out_dir)
        log(f"Wrote {out_filename}")
        return out_filename

    def check_requirements(self, filename, available_libs):
        reqs = []
        ef = ELFFile(open(filename, "rb"))
        dynamic = ef.get_section_by_name(".dynamic")
        if not dynamic:
            raise CommandError(f"{filename} has no .dynamic section")
        for tag in dynamic.iter_tags():
            if tag.entry.d_tag == "DT_NEEDED":
                req = COMPILER_LIBS.get(tag.needed)
                if req:
                    reqs.append(req)
                elif tag.needed in available_libs:
                    pass
                else:
                    raise CommandError(f"{filename} is linked against unknown library "
                                       f"'{tag.needed}'.")
        return reqs

    def get_requirements(self, req_type):
        reqs = []
        for req in self.package.meta["requirements"][req_type]:
            package, version = req.split()
            reqs.append((package, version))
        return reqs


class AndroidWheelBuilder(BaseWheelBuilder):
    def __init__(self, package, **kwargs):
        super().__init__(package, **kwargs)
        self.os = 'android'

    @classmethod
    def detect_toolchain(cls, toolchain):
        clang = f"{toolchain}/bin/clang"
        for word in open(clang).read().split():
            if word.startswith("--target"):
                match = re.search(r"^--target=(.+?)(\d+)$", word)
                if not match:
                    raise CommandError(f"Couldn't parse '{word}' in {clang}")

                for abi in ABIS['android']['android'].values():
                    if match[1] == abi.tool_prefix.replace("arm-", "armv7a-"):
                        abi_name = abi.name
                        break
                else:
                    raise CommandError(f"Unknown triplet '{match[1]}' in {clang}")

                api_level = int(match[2])
                standard_libs = sum((names for min_level, names in STANDARD_LIBS
                                          if api_level >= min_level),
                                         start=[])
                break
        else:
            raise CommandError(f"Couldn't find target in {clang}")

        log(f"Toolchain ABI: {abi_name}, API level: {api_level}")
        return abi, api_level, standard_libs

    def find_python(self):
        super().find_python()

        self.python_include_dir = f"{self.toolchain}/sysroot/usr/include/python{self.python_version}"
        assert_isdir(self.python_include_dir)
        libpython = f"libpython{self.python_version}.so"
        self.python_lib = f"{self.toolchain}/sysroot/usr/lib/{libpython}"
        assert_exists(self.python_lib)
        self.standard_libs.append(libpython)

    def platform_update_env(self, env):
        env["PATH"] = os.pathsep.join([
            f"{PYPI_DIR}/env/bin",
            f"{self.reqs_dir}/opt/bin",  # For "-config" scripts.
            env["PATH"]]
        )

        for tool in ["ar", "as", ("cc", "gcc"), ("cxx", "g++"),
                     ("fc", "gfortran"),   # Used by openblas
                     ("f77", "gfortran"), ("f90", "gfortran"),  # Used by numpy.distutils
                     "ld", "nm", "ranlib", "readelf", "strip"]:
            var, suffix = (tool, tool) if isinstance(tool, str) else tool
            filename = f"{self.toolchain}/bin/{self.abi.tool_prefix}-{suffix}"
            if suffix != "gfortran":  # Only required for SciPy and OpenBLAS.
                assert_exists(filename)
            env[var.upper()] = filename
        env["LDSHARED"] = f"{env['CC']} -shared"

        # If any flags are changed, consider also updating target/build-common-tools.sh.
        gcc_flags = " ".join([
            "-fPIC",  # See standalone toolchain docs, and note below about -pie
            self.abi.cflags])
        env["CFLAGS"] = gcc_flags
        env["FARCH"] = gcc_flags  # Used by numpy.distutils Fortran compilation.

        # If any flags are changed, consider also updating target/build-common-tools.sh.
        #
        # Not including -pie despite recommendation in standalone toolchain docs, because it
        # causes the linker to forget it's supposed to be building a shared library
        # (https://lists.debian.org/debian-devel/2016/05/msg00302.html). It can be added
        # manually for packages which require it (e.g. hdf5).
        env["LDFLAGS"] = " ".join([
            # This flag often catches errors in .so files which would otherwise be delayed
            # until runtime. (Some of the more complex build.sh scripts need to remove this, or
            # use it more selectively.)
            #
            # I tried also adding -Werror=implicit-function-declaration to CFLAGS, but that
            # breaks too many things (e.g. `has_function` in distutils.ccompiler).
            "-Wl,--no-undefined",

            # This currently only affects armeabi-v7a, but could affect other ABIs if the
            # unwinder implementation changes in a future NDK version
            # (https://android.googlesource.com/platform/ndk/+/ndk-release-r21/docs/BuildSystemMaintainers.md#Unwinding).
            # See also comment in build-fortran.sh.
            "-Wl,--exclude-libs,libgcc.a",       # NDK r18
            "-Wl,--exclude-libs,libgcc_real.a",  # NDK r19 and later
            "-Wl,--exclude-libs,libunwind.a",

            # Many packages get away with omitting this on standard Linux.
            "-lm",

            self.abi.ldflags])

        reqs_prefix = f"{self.reqs_dir}/opt"
        if exists(reqs_prefix):
            env["PKG_CONFIG_LIBDIR"] = f"{reqs_prefix}/lib/pkgconfig"
            env["CFLAGS"] += f" -I{reqs_prefix}/include"

            # --rpath-link only affects arm64, because it's the only ABI which uses ld.bfd. The
            # others all use ld.gold, which doesn't try to resolve transitive shared library
            # dependencies. When we upgrade to a later version of the NDK which uses LLD, we
            # can probably remove this flag, along with all requirements in meta.yaml files
            # which are tagged with "ld.bfd".
            env["LDFLAGS"] += (f" -L{reqs_prefix}/lib"
                               f" -Wl,--rpath-link,{reqs_prefix}/lib")

        env["ARFLAGS"] = "rc"

        # Set all unused overridable variables to the empty string to prevent the host Python
        # values (if any) from taking effect.
        for var in ["CPPFLAGS", "CXXFLAGS"]:
            env[var] = ""

        # Use -idirafter so that package-specified -I directories take priority (e.g. in grpcio
        # and typed-ast).
        if self.package.needs_python:
            env["CHAQUOPY_PYTHON"] = self.python_version
            env["CFLAGS"] = f" -idirafter {self.python_include_dir}"
            env["LDFLAGS"] = f" -lpython{self.python}"

    def process_native_binaries(self, tmp_dir, info_dir):
        SO_PATTERN = r"\.so(\.|$)"
        available_libs = set(self.standard_libs)
        for dir_name in [f"{self.reqs_dir}/opt/lib", tmp_dir]:
            if exists(dir_name):
                for _, _, filenames in os.walk(dir_name):
                    available_libs.update(name for name in filenames
                                          if re.search(SO_PATTERN, name))

        reqs = set()
        log("Processing native binaries")
        for path, _, _ in csv.reader(open(f"{info_dir}/RECORD")):
            is_shared = bool(re.search(SO_PATTERN, path))
            is_static = path.endswith(".a")
            is_executable = (path.startswith("chaquopy/bin/") and
                             not open(f"{tmp_dir}/{path}", "rb").read().startswith(b"#!"))
            if not any([is_executable, is_shared, is_static]):
                continue

            # Because distutils doesn't propertly support cross-compilation, native
            # modules will be tagged with the build platform, e.g.
            # `foo.cpython-36m-x86_64-linux-gnu.so`. Remove these tags.
            original_path = join(tmp_dir, path)
            fixed_path = re.sub(r"\.(cpython-[^.]+|abi3)\.so$", ".so", original_path)
            if fixed_path != original_path:
                run(f"mv {original_path} {fixed_path}")

            run(f"chmod +w {fixed_path}")
            run(f"{os.environ['STRIP']} --strip-unneeded {fixed_path}")

            if is_shared or is_executable:
                reqs.update(self.check_requirements(fixed_path, available_libs))
                # Paths from the build machine will be useless at runtime, unless they
                # use $ORIGIN, but that isn't supported until API level 24
                # (https://github.com/aosp-mirror/platform_bionic/blob/master/android-changes-for-ndk-developers.md).
                run(f"patchelf --remove-rpath {fixed_path}")

        return reqs

    def update_requirements(self, filename, reqs):
        msg = read_message(filename)
        for name, version in reqs:
            # If the package provides its own requirement, leave it unchanged.
            if not any(req.split()[0] == name
                    for req in msg.get_all("Requires-Dist", failobj=[])):
                req = f"{name} (>={version})"
                log(f"Adding requirement: {req}")
                # In this API, __setitem__ doesn't overwrite existing items.
                msg["Requires-Dist"] = req
        write_message(msg, filename)


class AppleWheelBuilder(BaseWheelBuilder):
    def __init__(self, os, package, **kwargs):
        super().__init__(package, **kwargs)
        self.os = os

    def find_python(self):
        super().find_python()

        self.python_include_dir = f"{self.toolchain}/{self.python_version}/Python.xcframework/{self.abi.slice}/Headers"
        assert_isdir(self.python_include_dir)
        self.python_lib = f"{self.toolchain}/{self.python_version}/Python.xcframework/{self.abi.slice}/libpython{self.python_version}.a"
        assert_exists(self.python_lib)

    def platform_update_env(self, env):
        # Make sure PATH is as clean as possible, to prevent leakage from
        # Homebrew or other local tools.

        # Python executable
        paths = [f"{sys.prefix}/bin"]

        # Cmake, if required
        if self.package.needs_cmake:
            cmake = f"{self.toolchain}/CMake.app"
            if not os.path.exists(cmake) or not os.path.isdir(cmake):
                raise CommandError(f"Couldn't find CMake.app in {self.toolchain}")
            paths.append(f"{self.toolchain}/CMake.app/Contents/bin"),

        # Add Bare macOS environment
        paths.extend([
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
            "/Library/Apple/usr/bin",
        ])

        env["PATH"] = os.pathsep.join(paths)

        env["CROSS_COMPILE_PLATFORM"] = f"{self.os}".lower()
        env["CROSS_COMPILE_PLATFORM_TAG"] = f"{self.os}_{self.api_level}_{self.abi.name}"
        env["CROSS_COMPILE_PREFIX"] = f"{self.toolchain}/{self.python_version}/Python.xcframework/{self.abi.slice}"
        env["CROSS_COMPILE_IMPLEMENTATION"] = self.abi.name

        sdk_root = subprocess.check_output(
            ["xcrun", "--show-sdk-path", "--sdk", self.abi.sdk],
            universal_newlines=True
        ).strip()
        env["CROSS_COMPILE_SDK_ROOT"] = sdk_root
        env["CROSS_COMPILE_TOOLCHAIN_SLICE"] = self.abi.slice

        env["CROSS_COMPILE_SYSCONFIGDATA"] = os.sep.join([
            self.toolchain, self.python_version, f"python-stdlib/_sysconfigdata__{self.os.lower()}_{self.abi.name}.py"
        ])

        config_globals = {}
        config_locals = {}
        with open(env["CROSS_COMPILE_SYSCONFIGDATA"]) as sysconfigdata:
            exec(sysconfigdata.read(), config_globals, config_locals)

            sysconfigdata = config_locals["build_time_vars"]

        for var in [
            "AR",
            "ARFLAGS",
            "BLDSHARED",
            "CFLAGS",
            "CC",
            "CXX",
            "CONFIGURE_CFLAGS",
            "CONFIGURE_LDFLAGS",
            "LDFLAGS",
            "LDSHARED",
        ]:
            orig_parts = split_quoted(config_locals["build_time_vars"][var])
            clean_parts = []
            for part in orig_parts:
                # An artefact of Python 3.8-3.10 is that the stdlib modules need to configured
                # using a global CFLAGS and LDFLAGS that point at the BZip2 and XZ builds, plus
                # the sysroot. The references to BZip2 and XZ include/lib folders aren't needed,
                # and the sysroot needs to be updated to reflect the currently active sysroot.
                if part.startswith("-I/Users") or part.startswith('-L/Users'):
                    pass
                elif part.startswith("--sysroot=/Applications/Xcode.app/Contents/Developer/Platforms/"):
                    clean_parts.append("--sysroot=" + env["CROSS_COMPILE_SDK_ROOT"])
                elif part.startswith('/Applications/Xcode.app/Contents/Developer/Platforms/'):
                    clean_parts.append(env["CROSS_COMPILE_SDK_ROOT"])
                else:
                    clean_parts.append(part)
            env[var] = ' '.join(clean_parts)

        reqs_prefix = f"{self.reqs_dir}/opt"
        if exists(reqs_prefix):
            env["CFLAGS"] += f" -I{reqs_prefix}/include"
            env["LDFLAGS"] += f" -L{reqs_prefix}/lib"

        # Use -idirafter so that package-specified -I directories take priority (e.g. in grpcio
        # and typed-ast).
        if self.package.needs_python:
            env["CHAQUOPY_PYTHON"] = self.python_version
            env["CFLAGS"] += f" -idirafter {self.python_include_dir}"

        # Update any reference to an sdk_root
        for key, value in env.items():
            if isinstance(value, str):
                value = re.sub(r"--sysroot=/.*?.sdk", f"--sysroot={sdk_root}",value)
                value = re.sub(r"-isysroot /.*?.sdk", f"-isysroot {sdk_root}", value)
            env[key] = value

    def process_native_binaries(self, tmp_dir, info_dir):
        # No post-processing required on the initial wheel binaries.
        return set()

    def update_requirements(self, filename, reqs):
        # No post-process of requirements
        pass

    @classmethod
    def api_level(cls, os, toolchain, python_version):
        with open(f"{toolchain}/{python_version}//VERSIONS") as f:
            for line in f.read().splitlines():
                if line.startswith(f"Min {os} version: "):
                    return line.split(':')[1].strip()
        raise CommandError("Couldn't read minimum API level from Apple support package")

    @classmethod
    def merge_wheels(cls, package, wheels, python_version, os, api_level):
        # Build a single platform compatibility tag
        if package.needs_python:
            compat_tag = (
                f"cp{python_version.replace('.', '')}-"
                f"cp{python_version.replace('.', '')}-"
                f"{os.lower()}_{api_level.replace('.', '_')}"
            )
        else:
            compat_tag = f"py{python_version[0]}-none-{os.lower()}_{api_level.replace('.', '_')}"

        merge_dir = f"{package.version_dir}/{compat_tag}"
        for sdk, architectures in wheels.items():
            for arch, wheel in architectures.items():
                # Unpack the source wheel into a shared folder.
                # This will overwrite every Python file with a copy of itself,
                # but any files that are different between SDKs will result
                # in a folder with both files.
                run(f"unzip -o -d {merge_dir} -q {wheel}")

            # All wheels for the same SDK should have the same list of binary artefacts.
            # Scan the RECORD entry for each wheel (it doesn't matter which one,
            # because the filename lists should be the same; so use the last one
            # that we iterated over)
            # Generate a fat binary in the "fix wheel" location for each
            # architecture in the sdk.
            SO_PATTERN = r"\.so(\.|$)"
            info_dir = f"{package.version_dir}/{compat_tag}_{sdk}_{arch}/fix_wheel/{package.name_version}.dist-info"
            for path, _, _ in csv.reader(open(f"{info_dir}/RECORD")):
                if bool(re.search(SO_PATTERN, path)):
                    fat_binary = f"{merge_dir}/{path}"
                    source_binaries = " ".join([
                        f"{package.version_dir}/{compat_tag}_{sdk}_{arch}/fix_wheel/{path}"
                        for arch in architectures.keys()
                    ])
                    run(f"lipo -create -o {fat_binary} {source_binaries}")

        # Repack a single wheel.
        out_dir = ensure_dir(f"{PYPI_DIR}/dist/{normalize_name_pypi(package.name)}")
        out_filename = package_wheel(package, compat_tag, merge_dir, out_dir)
        log(f"Wrote {out_filename}")


def find_license_files(path):
    return [f"{path}/{name}" for name in os.listdir(path)
            if re.search(r"^(LICEN[CS]E|COPYING)", name.upper())]


def update_message_file(filename, d, *args, **kwargs):
    try:
        msg = read_message(filename)
    except FileNotFoundError:
        msg = message.Message()
    update_message(msg, d, *args, **kwargs)
    write_message(msg, filename)
    return msg


def read_message(filename):
    return parser.Parser().parse(open(filename))


def package_wheel(package, compat_tag, in_dir, out_dir):
    build_num = str(package.meta["build"]["number"])
    info_dir = f"{in_dir}/{package.name_version}.dist-info"
    ensure_dir(info_dir)
    update_message_file(f"{info_dir}/WHEEL",
                        {"Wheel-Version": "1.0",
                            "Root-Is-Purelib": "false"},
                        if_exist="keep")
    update_message_file(f"{info_dir}/WHEEL",
                        {"Generator": PROGRAM_NAME,
                            "Build": build_num,
                            "Tag": compat_tag},
                        if_exist="replace")
    update_message_file(f"{info_dir}/METADATA",
                        {"Metadata-Version": "1.2",
                            "Name": package.name,
                            "Version": package.version,
                            "Summary": "",        # Compulsory according to PEP 345,
                            "Download-URL": ""},  #
                        if_exist="keep")
    run(f"wheel pack {in_dir} --dest-dir {out_dir} --build-number {build_num}")
    return join(out_dir, f"{package.name_version}-{build_num}-{compat_tag}.whl")


def update_message(msg, d, *, if_exist):
    for key, values in d.items():
        if if_exist == "keep":
            if key in msg:
                continue
        elif if_exist == "replace":
            del msg[key]  # Removes all items with this key.
        else:
            assert if_exist == "add", if_exist

        if not isinstance(values, list):
            values = [values]
        for value in values:
            msg[key] = value  # In this API, __setitem__ doesn't overwrite existing items.


def write_message(msg, filename):
    # I don't know whether maxheaderlen is required, but it's used by bdist_wheel.
    generator.Generator(open(filename, "w"), maxheaderlen=0).flatten(msg)


# See PEP 503.
def normalize_name_pypi(name):
    return re.sub(r"[-_.]+", "-", name).lower()

# This is what bdist_wheel does both for wheel filenames and .dist-info directory names.
# NOTE: this is not entirely equivalent to the specifications in PEP 427 and PEP 376.
def normalize_name_wheel(name):
    return re.sub(r"[^A-Za-z0-9.]+", '_', name)

#  e.g. "2017.01.02" -> "2017.1.2"
def normalize_version(version):
    return str(pkg_resources.parse_version(version))


def run(command, check=True):
    log(command)
    try:
        return subprocess.run(shlex.split(command), check=check)
    except subprocess.CalledProcessError as e:
        raise CommandError(f"Command returned exit status {e.returncode}")


def ensure_empty(dir_name):
    if exists(dir_name):
        run(f"rm -rf {dir_name}")
    return ensure_dir(dir_name)

def ensure_dir(dir_name):
    if not exists(dir_name):
        run(f"mkdir -p {dir_name}")
    return dir_name

def assert_isdir(filename):
    assert_exists(filename)
    if not isdir(filename):
        raise CommandError(f"{filename} is not a directory")
    return filename

def assert_exists(filename):
    if not exists(filename):
        raise CommandError(f"{filename} does not exist")


def cd(new_dir):
    if new_dir != os.getcwd():
        log(f"cd {new_dir}")
        os.chdir(new_dir)


def warn(s):
    log(f"Warning: {s}")

def log(s):
    print(f"{PROGRAM_NAME}: {s}")
    sys.stdout.flush()


class CommandError(Exception):
    pass


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--help", action="help", help=argparse.SUPPRESS)
    ap.add_argument("-v", "--verbose", action="store_true", help="Log more detail")

    skip_group = ap.add_mutually_exclusive_group()
    skip_group.add_argument(
        "--no-unpack",
        action="store_true",
        help="Skip download and unpack (an existing build/.../src directory must exist, and will be reused)"
    )
    skip_group.add_argument(
        "--no-build",
        action="store_true",
        help="Download and unpack, but skip build"
    )

    ap.add_argument(
        "--no-reqs",
        action="store_true",
        help="Skip extracting requirements (any existing build/.../requirements directory will be reused)"
    )
    ap.add_argument(
        "--toolchain",
        metavar="DIR",
        type=abspath,
        required=True,
        help="Path to toolchain"
    )
    ap.add_argument(
        "--python",
        metavar="X.Y",
        required=True,
        help="Python version (required for Python packages)"
    )
    ap.add_argument("--os", required=True, help="OS to build")
    ap.add_argument(
        "package_name_or_recipe",
        help=f"Name of a package in {RECIPES_DIR}, or if it contains a slash, path to a recipe directory"
    )
    ap.add_argument(
        "package_version",
        nargs="?",
        default=None,
        help="Package version to build (Optional; overrides version in meta.yaml)"
    )
    ap.add_argument(
        "build_number",
        type=int,
        nargs="?",
        default=None,
        help="Package build number to build (Optional; overrides version in meta.yaml)"
    )

    args = ap.parse_args()
    kwargs = vars(args)

    os = kwargs.pop("os")
    package_name_or_recipe = kwargs.pop("package_name_or_recipe")
    toolchain = kwargs.pop("toolchain")
    python_version = kwargs.pop("python")
    package_version = kwargs.pop("package_version")
    build_number = kwargs.pop("build_number")

    package = Package(package_name_or_recipe, package_version, build_number)

    if os == "android":
        abi, api_level, standard_libs = AndroidWheelBuilder.detect_toolchain(toolchain)
        builder = AndroidWheelBuilder(
            package,
            toolchain=toolchain,
            python_version=python_version,
            abi=abi,
            api_level=api_level,
            standard_libs=standard_libs,
            **kwargs,
        )

        builder.build()
    else:
        api_level = AppleWheelBuilder.api_level(os, toolchain, python_version)
        wheels = {}
        # Build a wheel for each supported ABI
        for sdk, architectures in ABIS[os].items():
            wheels[sdk] = {}
            for architcture, abi in architectures.items():
                builder = AppleWheelBuilder(
                    os,
                    package,
                    toolchain=toolchain,
                    python_version=python_version,
                    abi=abi,
                    api_level=api_level,
                    standard_libs=[],
                    **kwargs,
                )
                wheel = builder.build()
                if wheel:
                    wheels[sdk][architcture] = wheel

        # Merge the wheels into a single OS wheel.
        AppleWheelBuilder.merge_wheels(
            package,
            wheels,
            python_version=python_version,
            os=os,
            api_level=api_level,
        )


if __name__ == "__main__":
    try:
        main()
    except CommandError as e:
        log("Error: " + str(e))
        sys.exit(1)
