import builtins
from types import ModuleType


import_original = builtins.__import__

cpdef set_import_enabled(enable):
    """Sets whether the import hook is enabled. The import hook is enabled automatically when the
    `java` module is first loaded, so you only need to call this function if you want to
    disable it.
    """  # Further documentation in python.rst
    builtins.__import__ = import_override if enable else import_original


def import_override(name, globals={}, locals={}, fromlist=None, level=0):
    try:
        # When the module is found but some of the `fromlist` names aren't, an exception will
        # not be raised by import_original, and should not be raised by us either. The bytecode
        # in the caller is responsible for doing that.
        python_module = import_original(name, globals, locals, fromlist, level)
        python_exc = None
    except ImportError as e:
        python_module = None
        python_exc = clean_exception(e)
    except BaseException as e:
        raise clean_exception(e)

    if fromlist and (fromlist[0] != "*"):
        # We no longer detect clashes between Python and Java names, because looking up all the
        # Python names in Java was slowing down Python imports too much. Instead, we only look up
        # any names that Python failed to find.
        python_names = []
        missing_names = []
        for from_name in fromlist:
            (python_names if ((python_module is not None) and hasattr(python_module, from_name))
             else missing_names).append(from_name)

        if missing_names:
            from_pkg = resolve_name(name, globals, level)
            java_imports = {}
            for from_name in missing_names:
                try:
                    java_imports[from_name] = jclass(f"{from_pkg}.{from_name}")
                except NoClassDefFoundError:
                    pass  # See note at call to import_original.

            if java_imports:
                # Don't add the Java classes as attributes of the Python module: that would be
                # confusing. Instead, return a temporary module object containing the merged set of
                # names found in both languages.
                module = ModuleType("<java import hook>")
                module.__dict__.update(java_imports)
                for from_name in python_names:
                    setattr(module, from_name, getattr(python_module, from_name))
                return module

    # If we got this far, we didn't import anything at all from Java, so return exactly what
    # import_original did.
    if python_exc:
        raise python_exc
    return python_module


# Reduce noise in exception traces by removing frames from the import system. (The interpreter
# only does this for the standard import system: see remove_import_frames in Python/import.c.)
def clean_exception(e):
    tb = e.__traceback__
    while in_import_system(tb.tb_frame.f_code.co_filename):
        tb = tb.tb_next
        if tb is None:
            # A file with a SyntaxError is not actually in the traceback, because it was never
            # compiled successfully.
            if isinstance(e, SyntaxError) and not in_import_system(e.filename):
                break
            else:
                # The exception originated within the import system, so return it untouched to
                # assist debugging.
                return e
    return e.with_traceback(tb)


def in_import_system(filename):
    return (filename == "import.pxi" or
            filename.startswith("<frozen importlib") or
            filename.endswith("/java/android/importer.py"))


cdef resolve_name(name, globals, level):
    if level > 0:  # Relative import
        current_pkg = globals.get("__package__")
        if current_pkg is None:  # Empty string indicates a top-level module.
            spec = globals.get("__spec__")
            if spec:
                current_pkg = spec.parent
            else:
                mod_name = globals["__name__"]
                current_pkg = mod_name if "__path__" in globals else mod_name.rpartition(".")[0]
        if not isinstance(current_pkg, str):
            raise TypeError('__package__ not set to a string')

        current_pkg_split = current_pkg.split(".")
        if (level - 1) >= len(current_pkg_split):  # http://bugs.python.org/issue30840
            raise ValueError("attempted relative import beyond top-level package")
        prefix_len = len(current_pkg_split) - (level - 1)
        base_pkg = '.'.join(current_pkg_split[:prefix_len])
        return f"{base_pkg}.{name}" if name else base_pkg

    else:  # Absolute import
        return name


class AssetFile(object):
    # `path` is relative to the assets root. Raises java.io.IOException if the asset does not
    # exist.
    def __init__(self, context, path):
        self.name = path
        self.stream = AssetFile_get_stream(context, path)
        self.stream.mark(2**31 - 1)
        self.offset = 0
        self.length = self.stream.available()

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r})"

    def read(self, size=None):
        if size is None:
            size = self.stream.available()
        array = jarray("B")(size)
        read_len = self.stream.read(array)
        if read_len == -1:
            return b""
        self.offset += read_len
        return array.__bytes__(0, read_len)

    def seek(self, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            pass
        elif whence == os.SEEK_CUR:
            offset = self.offset + offset
        elif whence == os.SEEK_END:
            offset = self.length + offset
        else:
            raise ValueError("unsupported whence: {}".format(whence))

        self.stream.reset()
        self.stream.skip(offset)
        self.offset = offset
        return offset

    def tell(self):
        return self.offset

    def close(self):
        self.stream.close()
        self.stream = None


IF CHAQUOPY_LICENSE_MODE not in ["ec"]:
    # Can't use the import statment in this function, or infinite recursion will happen during
    # importer initialization.
    def AssetFile_get_stream(context, s):
        AssetManager = jclass("android.content.res.AssetManager")
        return context.getAssets().open(s, AssetManager.ACCESS_RANDOM)
