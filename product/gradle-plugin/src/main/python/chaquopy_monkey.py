import os
import sys
import types


# We want to cause a quick and comprehensible failure when a package attempts to build
# native code, while still allowing a pure-Python fallback if available. This is tricky,
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
    disable_native_distutils()
    disable_native_environ()


def disable_native_distutils():
    # Recent versions of setuptools redirect distutils to their own bundled copy, so try
    # to import that first. Even more recent versions of setuptools provide a .pth file
    # which makes this import unnecessary, but the package we're installing might have
    # pinned an older version in its pyproject.toml file.
    try:
        import setuptools  # noqa: F401
    except ImportError:
        pass

    try:
        import distutils  # noqa: F401
    except ImportError:
        # distutils was removed in Python 3.12, so it will only exist if setuptools is
        # in the build environment.
        return

    from distutils import ccompiler
    from distutils.unixccompiler import UnixCCompiler

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

    disabled_mod_name = "distutils.disabledcompiler"
    disabled_mod = types.ModuleType(disabled_mod_name)
    disabled_mod.DisabledCompiler = DisabledCompiler
    sys.modules[disabled_mod_name] = disabled_mod


def disable_native_environ():
    # Try to disable native builds for packages which don't use the distutils native build
    # system at all (e.g. uwsgi), or only use it to wrap an external build script (e.g. pynacl).
    for tool in ["ar", "as", "cc", "cxx", "ld"]:
        os.environ[tool.upper()] = CHAQUOPY_NATIVE_ERROR.replace(" ", "_")


CHAQUOPY_NATIVE_ERROR = "Chaquopy cannot compile native code"

def chaquopy_block_native(prefix):
    # No need to give any more advice here: that will come from the higher-level code in pip.
    from distutils.errors import DistutilsPlatformError
    raise DistutilsPlatformError("{}: {}".format(prefix, CHAQUOPY_NATIVE_ERROR))
