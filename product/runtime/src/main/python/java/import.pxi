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

    tb_clean = []
    while tb:
        if not in_import_system(tb.tb_frame.f_code.co_filename):
            tb_clean.append(tb)
        tb = tb.tb_next

    # A file with a SyntaxError is not actually in the traceback, because it was never
    # compiled successfully.
    if tb_clean or isinstance(e, SyntaxError):
        # Construct a traceback from the non-import-system frames only.
        for i, tb in enumerate(tb_clean):
            tb.tb_next = (
                None if i + 1 == len(tb_clean)
                else tb_clean[i + 1]
            )
        return e.with_traceback(tb_clean[0] if tb_clean else None)
    else:
        # All frames came from the import system, so return the exception untouched to
        # assist debugging.
        return e

def in_import_system(filename):
    filename = filename.replace("\\", "/")  # For .pyc files compiled on Windows.
    return (filename in ["import.pxi", "stdlib/zipfile.py"] or
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
