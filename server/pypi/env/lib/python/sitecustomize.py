# build-wheel sets PYTHONPATH to ensure this file is imported on startup in pip and all of
# its Python subprocesses.
#
# build-wheel currently disables all pyproject.toml files by renaming them. At some point
# we'll have to stop doing this in order to enable PEP 517 builds. However, pip overrides
# PYTHONPATH when launching a PEP 517 build, which will prevent this file from taking
# effect in the subprocess. So we may need to use a different approach, perhaps even using
# a different PEP 517 front end like pypa/build.

import os
from os.path import abspath, commonpath
import sys

from setuptools._distutils import ccompiler, dist, sysconfig, util


# --no-clean currently has no effect when running `pip wheel`
# (https://github.com/pypa/pip/issues/5661), so disable the clean command to prevent it
# destroying the evidence after a build failure. Monkey-patching at this level also handles
# packages overriding the `clean` command using `cmdclass.`
run_command_original = dist.Distribution.run_command

def run_command_override(self, command):
    if command == "clean":
        print("Chaquopy: clean command disabled")
    else:
        run_command_original(self, command)

dist.Distribution.run_command = run_command_override


# Remove include and library directories which are not in known safe locations.
# Monkey-patching at this level handles both default paths added by distutils itself,
# and paths added explicitly by package build scripts.
# We must also allow include directories from env/ dir 
# as they contain pybind11/pybind11.h headers needed to build some packages like scipy
src_dir = os.environ["SRC_DIR"]
valid_dirs = [abspath(path) for path in [src_dir, f"{src_dir}/../requirements", f"{src_dir}/../env"]]

def filter_dirs(dir_type, dirs):
    result = []
    for dir in dirs:
        if any(commonpath([vd, abspath(dir)]) == vd for vd in valid_dirs):
            result.append(dir)
        else:
            print(f"Chaquopy: ignored invalid {dir_type} directory: {dir!r}")
    return result


gen_preprocess_options_original = ccompiler.gen_preprocess_options

def gen_preprocess_options_override(macros, include_dirs):
    return gen_preprocess_options_original(macros, filter_dirs("include", include_dirs))

ccompiler.gen_preprocess_options = gen_preprocess_options_override


gen_lib_options_original = ccompiler.gen_lib_options

def gen_lib_options_override(compiler, library_dirs, runtime_library_dirs, libraries):
    return gen_lib_options_original(
        compiler, filter_dirs("library", library_dirs), runtime_library_dirs, libraries)

ccompiler.gen_lib_options = gen_lib_options_override


# Override the CFLAGS from the build Python sysconfigdata file.
# TODO: look into using crossenv to extract this from the Android sysconfigdata.
sysconfig.get_config_vars()  # Ensure _config_vars has been initialized.
sysconfig._config_vars["CFLAGS"] = \
    "-Wno-unused-result -Wsign-compare -Wunreachable-code -DNDEBUG -g -fwrapv -O3 -Wall"


# Fix distutils ignoring LDFLAGS when building executables.
customize_compiler_original = sysconfig.customize_compiler

def customize_compiler_override(compiler):
    customize_compiler_original(compiler)
    ldflags = os.environ["LDFLAGS"]
    if ldflags not in " ".join(compiler.linker_exe):
        compiler.linker_exe += util.split_quoted(ldflags)

sysconfig.customize_compiler = customize_compiler_override


# Call the next sitecustomize script if there is one
# (https://nedbatchelder.com/blog/201001/running_code_at_python_startup.html).
del sys.modules["sitecustomize"]
this_dir = os.path.dirname(__file__)
path_index = sys.path.index(this_dir)
del sys.path[path_index]
try:
    import sitecustomize  # noqa: F401
finally:
    sys.path.insert(path_index, this_dir)
