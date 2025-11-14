# build-wheel sets PYTHONPATH to ensure this file is imported on startup in all of
# its Python subprocesses.

import os
import shlex
import sys

# Recent versions of setuptools redirect distutils to their own bundled copy, so try
# to import that first. Even more recent versions of setuptools provide a .pth file
# which makes this import unnecessary, but the package we're building might have
# pinned an older version in its pyproject.toml file.
try:
    import setuptools  # noqa: F401
except ImportError:
    pass

try:
    from distutils import sysconfig
except ImportError:
    # distutils was removed in Python 3.12, so it will only exist if setuptools is
    # in the build environment.
    pass
else:
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
            compiler.linker_exe += shlex.split(ldflags)

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
