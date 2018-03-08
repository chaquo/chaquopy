from types import ModuleType

builtins = six.moves.builtins
import_original = builtins.__import__

cpdef set_import_enabled(enable):
    """Sets whether the import hook is enabled. The import hook is enabled automatically when the
    `java` module is first loaded, so you only need to call this function if you want to
    disable it.
    """  # Further documentation in python.rst
    builtins.__import__ = import_override if enable else import_original


def import_override(name, globals={}, locals={}, fromlist=None,
                    level=-1 if six.PY2 else 0):
    try:
        python_module = import_original(name, globals, locals, fromlist, level)
        python_exc_info = None
    except ImportError:
        python_module = None
        python_exc_info = sys.exc_info()

    if fromlist and (fromlist[0] != "*"):
        from_pkg = resolve_name(name, globals, level)
        java_imports = {}
        for from_name in fromlist:
            try:
                cls = jclass(f"{from_pkg}.{from_name}")
                java_imports[from_name] = cls
            except NoClassDefFoundError:
                pass  # The caller is responsible for raising ImportError if some names aren't found.

        if java_imports:
            # If there's a Python module of the same name, don't add the Java imports to it as
            # attributes. Instead, return a new module object containing only the requested names.
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

    if python_exc_info:
        six.reraise(*python_exc_info)
    return python_module


# Exception types and wording are based on Python 3.5.
cdef resolve_name(name, globals, level):
    if level > 0:   # Explicit relative import
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

    else:           # Absolute import (Python 2 implicit relative import is not attempted)
        return name
