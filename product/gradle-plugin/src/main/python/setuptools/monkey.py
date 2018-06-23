"""
Monkey patching of distutils.
"""

import sys
import distutils.filelist
import platform
import types
import functools
from importlib import import_module
import inspect

from setuptools.extern import six

import setuptools

__all__ = []
"""
Everything is private. Contact the project team
if you think you need this functionality.
"""


def _get_mro(cls):
    """
    Returns the bases classes for cls sorted by the MRO.

    Works around an issue on Jython where inspect.getmro will not return all
    base classes if multiple classes share the same name. Instead, this
    function will return a tuple containing the class itself, and the contents
    of cls.__bases__. See https://github.com/pypa/setuptools/issues/1024.
    """
    if platform.python_implementation() == "Jython":
        return (cls,) + cls.__bases__
    return inspect.getmro(cls)


def get_unpatched(item):
    lookup = (
        get_unpatched_class if isinstance(item, six.class_types) else
        get_unpatched_function if isinstance(item, types.FunctionType) else
        lambda item: None
    )
    return lookup(item)


def get_unpatched_class(cls):
    """Protect against re-patching the distutils if reloaded

    Also ensures that no other distutils extension monkeypatched the distutils
    first.
    """
    external_bases = (
        cls
        for cls in _get_mro(cls)
        if not cls.__module__.startswith('setuptools')
    )
    base = next(external_bases)
    if not base.__module__.startswith('distutils'):
        msg = "distutils has already been patched by %r" % cls
        raise AssertionError(msg)
    return base


def patch_all():
    # we can't patch distutils.cmd, alas
    distutils.core.Command = setuptools.Command

    has_issue_12885 = sys.version_info <= (3, 5, 3)

    if has_issue_12885:
        # fix findall bug in distutils (http://bugs.python.org/issue12885)
        distutils.filelist.findall = setuptools.findall

    needs_warehouse = (
        sys.version_info < (2, 7, 13)
        or
        (3, 0) < sys.version_info < (3, 3, 7)
        or
        (3, 4) < sys.version_info < (3, 4, 6)
        or
        (3, 5) < sys.version_info <= (3, 5, 3)
    )

    if needs_warehouse:
        warehouse = 'https://upload.pypi.org/legacy/'
        distutils.config.PyPIRCCommand.DEFAULT_REPOSITORY = warehouse

    _patch_distribution_metadata_write_pkg_file()

    # Install Distribution throughout the distutils
    for module in distutils.dist, distutils.core, distutils.cmd:
        module.Distribution = setuptools.dist.Distribution

    # Install the patched Extension
    distutils.core.Extension = setuptools.extension.Extension
    distutils.extension.Extension = setuptools.extension.Extension
    if 'distutils.command.build_ext' in sys.modules:
        sys.modules['distutils.command.build_ext'].Extension = (
            setuptools.extension.Extension
        )

    # Chaquopy disabled: importing distutils.msvc9compiler causes exception "not supported by
    # this module" on MSYS2 Python, because it isn't built with MSVC.
    # patch_for_msvc_specialized_compiler()

    disable_native()


# Chaquopy: We want to cause a quick and comprehensible failure when a package attempts to
# build native code, while still allowing a pure-Python fallback if available. This is tricky,
# because different packages have different approaches to pure-Python fallbacks:
#
# * Some packages simply catch any distutils exception thrown by setup(), and then run it again
#   with the native components removed.
#
# * Some (e.g. sqlalchemy, wrapt) extend the distutils build_ext or build_clib command and
#   override its run() method to wrap it with an exception handler. This means we can't simply
#   block the commands by name, e.g. by overriding Distribution.run_command.
#
# * Some (e.g. msgpack) go lower-level and catch exceptions in build_ext.build_extension. In
#   Python 3, there's an `optional` keyword to Extension which has the same effect (used e.g.
#   by websockets). Blocking build_ext.run, or CCompiler.__init__, would cause these builds to
#   fail before build_extension is called, and the pure-Python fallback wouldn't happen.
#
# Creating a new compiler class with a new name minimizes the chance of code trying to do
# things which will only work on the standard classses. For example,
# distutils.sysconfig.customize_compiler does things with a "unix" compiler which will crash on
# Windows because get_config_vars won't have certain settings.
#
# This is simpler than determining the regular compiler class and extending it. It avoids
# interference from NumPy's widespread monkey-patching (including new_compiler, CCompiler and
# its subclasses), which takes place after this code is run. It also avoids the default
# behaviour on Windows when no compiler is installed, which is either to give the "Unable to
# find vcvarsall.bat" error, or advice on how to install Visual C++, both of which will waste
# the user's time.
#
# This approach will block builds of packages which require the compiler name to be in a known
# list (e.g. minorminer, lz4), but the error messages from these packages aren't too bad, and
# I've never seen one which has a pure-Python fallback.
def disable_native():
    from distutils import ccompiler
    from distutils.unixccompiler import UnixCCompiler
    import os
    import types

    ccompiler.get_default_compiler = lambda *args, **kwargs: "disabled"
    ccompiler.compiler_class["disabled"] = (
        "disabledcompiler", "DisabledCompiler",
        "Compiler disabled ({})".format(CHAQUOPY_NATIVE_ERROR))

    class DisabledCompiler(ccompiler.CCompiler):
        compiler_type = "disabled"
        def preprocess(*args, **kwargs):
            chaquopy_block_native("CCompiler.preprocess")
        def compile(*args, **kwargs):
            chaquopy_block_native("CCompiler.compile")
        def create_static_lib(*args, **kwargs):
            chaquopy_block_native("CCompiler.create_static_lib")
        def link(*args, **kwargs):
            chaquopy_block_native("CCompiler.link")

    # To maximize the chance of the build getting as far as actually calling compile(), make
    # sure the class has all of the expected attributes.
    for name in ["src_extensions", "obj_extension", "static_lib_extension",
                 "shared_lib_extension", "static_lib_format", "shared_lib_format",
                 "exe_extension"]:
        setattr(DisabledCompiler, name, getattr(UnixCCompiler, name))
    DisabledCompiler.executables = {name: [CHAQUOPY_NATIVE_ERROR.replace(" ", "_")]
                                    for name in UnixCCompiler.executables}

    disabled_mod = types.ModuleType("distutils.disabledcompiler")
    disabled_mod.DisabledCompiler = DisabledCompiler
    sys.modules["distutils.disabledcompiler"] = disabled_mod

    # Try to disable native builds for packages which don't use the distutils native build
    # system at all (e.g. uwsgi), or only use it to wrap an external build script (e.g. pynacl).
    for tool in ["ar", "as", "cc", "cxx", "ld"]:
        os.environ[tool.upper()] = CHAQUOPY_NATIVE_ERROR.replace(" ", "_")


CHAQUOPY_NATIVE_ERROR = "Chaquopy cannot compile native code"

def chaquopy_block_native(prefix):
    # No need to give any more advice here: that will come from the higher-level code in pip.
    from distutils.errors import DistutilsPlatformError
    raise DistutilsPlatformError("{}: {}".format(prefix, CHAQUOPY_NATIVE_ERROR))


def _patch_distribution_metadata_write_pkg_file():
    """Patch write_pkg_file to also write Requires-Python/Requires-External"""
    distutils.dist.DistributionMetadata.write_pkg_file = (
        setuptools.dist.write_pkg_file
    )


def patch_func(replacement, target_mod, func_name):
    """
    Patch func_name in target_mod with replacement

    Important - original must be resolved by name to avoid
    patching an already patched function.
    """
    original = getattr(target_mod, func_name)

    # set the 'unpatched' attribute on the replacement to
    # point to the original.
    vars(replacement).setdefault('unpatched', original)

    # replace the function in the original module
    setattr(target_mod, func_name, replacement)


def get_unpatched_function(candidate):
    return getattr(candidate, 'unpatched')


def patch_for_msvc_specialized_compiler():
    """
    Patch functions in distutils to use standalone Microsoft Visual C++
    compilers.
    """
    # import late to avoid circular imports on Python < 3.5
    msvc = import_module('setuptools.msvc')

    if platform.system() != 'Windows':
        # Compilers only availables on Microsoft Windows
        return

    def patch_params(mod_name, func_name):
        """
        Prepare the parameters for patch_func to patch indicated function.
        """
        repl_prefix = 'msvc9_' if 'msvc9' in mod_name else 'msvc14_'
        repl_name = repl_prefix + func_name.lstrip('_')
        repl = getattr(msvc, repl_name)
        mod = import_module(mod_name)
        if not hasattr(mod, func_name):
            raise ImportError(func_name)
        return repl, mod, func_name

    # Python 2.7 to 3.4
    msvc9 = functools.partial(patch_params, 'distutils.msvc9compiler')

    # Python 3.5+
    msvc14 = functools.partial(patch_params, 'distutils._msvccompiler')

    try:
        # Patch distutils.msvc9compiler
        patch_func(*msvc9('find_vcvarsall'))
        patch_func(*msvc9('query_vcvarsall'))
    except ImportError:
        pass

    try:
        # Patch distutils._msvccompiler._get_vc_env
        patch_func(*msvc14('_get_vc_env'))
    except ImportError:
        pass

    try:
        # Patch distutils._msvccompiler.gen_lib_options for Numpy
        patch_func(*msvc14('gen_lib_options'))
    except ImportError:
        pass
