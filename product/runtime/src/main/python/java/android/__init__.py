"""Copyright (c) 2018 Chaquo Ltd. All rights reserved."""

from importlib import import_module, reload
import os
from os.path import exists, join
import sys
import traceback
from . import stream, importer


def initialize(context, build_json, app_path):
    stream.initialize()
    importer.initialize(context, build_json, app_path)
    initialize_stdlib(context)


def initialize_stdlib(context):
    from com.chaquo.python import Common
    initialize_sys(context, Common)
    initialize_os(context)
    initialize_sysconfig(context, Common)
    initialize_tempfile(context)
    initialize_ssl(context)
    initialize_hashlib(context)
    initialize_ctypes(context)


def initialize_sys(context, Common):
    if sys.version_info[0] >= 3:
        sys.abiflags = Common.PYTHON_SUFFIX[len(Common.PYTHON_VERSION_SHORT):]

    # argv defaults to not existing, which may crash some programs.
    sys.argv = [""]

    # executable defaults to "python" on 2.7, or "" on 3.6. But neither of these values (or
    # None, which is mentioned in the documentation) will allow platform.platform() to run
    # without crashing.
    try:
        sys.executable = os.readlink("/proc/{}/exe".format(os.getpid()))
    except Exception:
        # Can't be certain that /proc will work on all devices, so try to carry on.
        traceback.print_exc()
        sys.executable = ""

    # Remove default paths (#5410).
    invalid_paths = [p for p in sys.path
                     if not (exists(p) or p.startswith(importer.ASSET_PREFIX))]
    for p in invalid_paths:
        sys.path.remove(p)


def initialize_os(context):
    # By default, os.path.expanduser("~") returns "/data", which is an unwritable directory.
    # Make it return something more usable.
    os.environ.setdefault("HOME", str(context.getFilesDir()))


def initialize_sysconfig(context, Common):
    # Put a few basic things in until the build process is fixed to generate this (#5160).
    import sys
    import _sysconfigdata
    _sysconfigdata.build_time_vars.update({
        "EXT_SUFFIX": ".so",
        "LIBDIR": sys.prefix,
        "LDLIBRARY": f"libpython{Common.PYTHON_SUFFIX}.so"
    })

    if sys.version_info[0] >= 3:
        # distutils.sysconfig expects this module to exist.
        mod_name = '_sysconfigdata_{}_{}_{}'.format(
            sys.abiflags, sys.platform,
            getattr(sys.implementation, '_multiarch', ''))
        sys.modules[mod_name] = _sysconfigdata


def initialize_tempfile(context):
    tmpdir = join(str(context.getCacheDir()), "chaquopy/tmp")
    if not exists(tmpdir):
        os.makedirs(tmpdir)
    os.environ["TMPDIR"] = tmpdir


def initialize_ssl(context):
    # OpenSSL actually does know the location of the system CA store on Android, but
    # unfortunately there are multiple incompatible formats of that location, so we can't rely
    # on it (https://blog.kylemanna.com/android/android-ca-certificates/).
    os.environ["SSL_CERT_FILE"] = join(str(context.getFilesDir()), "chaquopy/cacert.pem")


def initialize_hashlib(context):
    # hashlib may already have been imported during bootstrap: reload it now that the the
    # OpenSSL interface in `_hashlib` is on sys.path.
    import hashlib
    reload(hashlib)

    for mod_name in ["_blake2", "_sha3"]:
        try:
            import_module(mod_name)
            raise Exception(f"module {mod_name} is available: workaround should be removed")
        except ImportError:
            pass

    # None of the native hash modules are currently included on this branch. hashlib will
    # normally prefer to use OpenSSL anyway, which works for MD5, SHA-1 and SHA-2, but we need
    # to intervene for BLAKE2 and SHA-3 because they're given different identifiers by OpenSSL.
    # This technique should enable everything in the hashlib documentation, except the
    # additional keyword arguments for BLAKE2.
    NAME_MAP = {f"sha3_{n}": f"sha3-{n}" for n in [224, 256, 384, 512]}
    NAME_MAP.update({"blake2b": "blake2b512", "blake2s": "blake2s256"})
    def new_constructor(name):
        return lambda data=b"": hashlib.new(name, data)
    for python_name, openssl_name in NAME_MAP.items():
        setattr(hashlib, python_name, new_constructor(openssl_name))

    new_original = hashlib.new
    def new_override(name, data=b""):
        return new_original(NAME_MAP.get(name, name), data)
    hashlib.new = new_override


def initialize_ctypes(context):
    import ctypes.util
    import sysconfig

    # The standard implementation of find_library requires external tools, so will always fail
    # on Android. I can't see any easy way of finding the absolute library pathname ourselves
    # (there is no LD_LIBRARY_PATH on Android), but we can at least support the case where the
    # user passes the return value of find_library to CDLL().
    def find_library_override(name):
        filename = "lib{}.so".format(name)
        try:
            ctypes.CDLL(filename)
        except OSError:
            return None
        else:
            return filename
    ctypes.util.find_library = find_library_override

    ctypes.pythonapi = ctypes.PyDLL(sysconfig.get_config_vars()["LDLIBRARY"])
