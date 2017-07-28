from six.moves import builtins
import sys
from types import ModuleType


import_original = builtins.__import__

def set_import_enabled(enable):
    """Sets whether the import hook is enabled. The import hook is enabled automatically when the
    `java` module is first loaded, so you only need to call this function if you want to
    disable it.
    """  # Further documentation in python.rst
    builtins.__import__ = import_override if enable else import_original


def import_override(name, globals={}, locals={}, fromlist=None, level=0):
    try:
        python_module = import_original(name, globals, locals, fromlist, level)
        python_error = python_tb = None
    except ImportError as e:
        python_module = None
        python_error = e
        python_tb = sys.exc_info()[2]

    if fromlist and (fromlist[0] != "*"):
        from_pkg = resolve_name(name, globals, level)
        java_imports = {}
        for from_name in fromlist:
            try:
                cls = java.jclass(f"{from_pkg}.{from_name}")
                java_imports[from_name] = cls
            except JavaException:
                pass  # The caller is responsible for raising ImportError if some names aren't found.

        if java_imports:
            # Don't add attributes to the Python module of the same name, that would be confusing.
            module = ModuleType("<java import hook>")
            if python_module:
                for from_name in fromlist:
                    try:
                        setattr(module, from_name, getattr(python_module, from_name))
                    except AttributeError: pass
            for from_name, cls in six.iteritems(java_imports):
                if hasattr(module, from_name):
                    raise ImportError(f"{from_pkg}.{from_name} exists in both Java and Python. "
                                      f"Access the Java copy with jclass('{from_pkg}."
                                      f"{from_name}'), and the Python copy with 'import "
                                      f"{from_pkg}' followed by '{from_pkg}.{from_name}'.")
                setattr(module, from_name, cls)
            return module

    if python_error:
        six.reraise(ImportError, python_error, python_tb)
    return python_module


# Exception types and wording are based on Python 3.5.
def resolve_name(name, globals, level):
    if level > 0:   # Explicit relative import
        try:
            current_pkg = globals["__package__"]
        except KeyError:
            raise ImportError("attempted relative import with no known parent package")
        if not isinstance(current_pkg, str):
            raise TypeError('__package__ not set to a string')

        current_pkg_split = current_pkg.split(".")
        if (level - 1) >= len(current_pkg_split):  # http://bugs.python.org/issue30840
            raise ValueError("attempted relative import beyond top-level package")
        prefix_len = len(current_pkg_split) - (level - 1)
        base_pkg = '.'.join(current_pkg_split[:prefix_len])
        return f"{base_pkg}.{name}" if name else base_pkg

    else:           # Absolute import (Python 2 implicit relative import is not attempted)
        return name
