# This file is imported on startup in pip and all of its Python subprocesses.

import os
import sys


# --no-clean currently has no effect when running `pip wheel`
# (https://github.com/pypa/pip/issues/5661), so disable the clean command to prevent it
# destroying the evidence after a build failure. Monkey-patching at this level also handles
# packages overriding the `clean` command using `cmdclass.`
from distutils.dist import Distribution
run_command_original = Distribution.run_command

def run_command_override(self, command):
    if command == "clean":
        print("Chaquopy: clean command disabled")
    else:
        run_command_original(self, command)

Distribution.run_command = run_command_override


# Remove include paths for the build Python, including any virtualenv. Monkey-patching at this
# level handles both default paths added by distutils itself, and paths added explicitly by
# setup.py scripts.
import distutils.ccompiler
gen_preprocess_options_original = distutils.ccompiler.gen_preprocess_options

def gen_preprocess_options_override(macros, include_dirs):
    include_dirs = [
        item for item in include_dirs
        if item not in [distutils.sysconfig.get_python_inc(),
                        distutils.sysconfig.get_python_inc(plat_specific=True),
                        os.path.join(sys.exec_prefix, 'include')]]
    return gen_preprocess_options_original(macros, include_dirs)

distutils.ccompiler.gen_preprocess_options = gen_preprocess_options_override


# Fix distutils ignoring LDFLAGS when building executables.
import distutils.sysconfig
from distutils.util import split_quoted
customize_compiler_original = distutils.sysconfig.customize_compiler

def customize_compiler_override(compiler):
    customize_compiler_original(compiler)
    ldflags = os.environ["LDFLAGS"]
    if ldflags not in " ".join(compiler.linker_exe):
        compiler.linker_exe += split_quoted(ldflags)

distutils.sysconfig.customize_compiler = customize_compiler_override


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
