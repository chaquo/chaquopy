import sys

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import List

# Shim to wrap setup.py invocation with setuptools
#
# We set sys.argv[0] to the path to the underlying setup.py file so
# setuptools / distutils don't take the path to the setup.py to be "-c" when
# invoking via the shim.  This avoids e.g. the following manifest_maker
# warning: "warning: manifest_maker: standard file '-c' not found".
_SETUPTOOLS_SHIM = (
    "import sys, setuptools, tokenize; sys.argv[0] = {0!r}; __file__={0!r};"
    "{chaquopy_monkey};"
    "f=getattr(tokenize, 'open', open)(__file__);"
    "code=f.read().replace('\\r\\n', '\\n');"
    "f.close();"
    "exec(compile(code, __file__, 'exec'))"
)


def make_setuptools_shim_args(setup_py_path, unbuffered_output=False):
    # type: (str, bool) -> List[str]
    """
    Get setuptools command arguments with shim wrapped setup file invocation.

    :param setup_py_path: The path to setup.py to be wrapped.
    :param unbuffered_output: If True, adds the unbuffered switch to the
     argument list.
    """
    args = [sys.executable]
    if unbuffered_output:
        args.append('-u')

    # Chaquopy: added '-S' to avoid interference from site-packages. This makes
    # non-installable packages fail more quickly and consistently. Also, some packages
    # (e.g. Cython) install distutils hooks which can interfere with our attempts to
    # disable compilers in chaquopy_monkey.
    args.append('-S')

    from pip._vendor.packaging import markers
    chaquopy_monkey = (
        "import chaquopy_monkey; chaquopy_monkey.disable_native()"
        if markers.python_version_info
        else "pass"
    )
    args.extend(['-c', _SETUPTOOLS_SHIM.format(setup_py_path,
                                               chaquopy_monkey=chaquopy_monkey)])
    return args
