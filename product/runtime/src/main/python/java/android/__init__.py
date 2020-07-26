"""Copyright (c) 2020 Chaquo Ltd. All rights reserved."""

from importlib import reload
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
    # These are ordered roughly from low to high level.
    for name in ["sys", "os", "tempfile", "ssl", "hashlib", "multiprocessing"]:
        globals()[f"initialize_{name}"](context)


def initialize_sys(context):
    from com.chaquo.python import Common
    sys.abiflags = Common.PYTHON_SUFFIX[len(Common.PYTHON_VERSION_SHORT):]

    # argv defaults to not existing, which may crash some programs.
    sys.argv = [""]

    # executable defaults to the empty string, but this causes platform.platform() to crash.
    try:
        sys.executable = os.readlink("/proc/{}/exe".format(os.getpid()))
    except Exception:
        # Can't be certain that /proc will work on all devices, so try to carry on.
        traceback.print_exc()
        sys.executable = ""


def initialize_os(context):
    # By default, os.path.expanduser("~") returns "/data", which is an unwritable directory.
    # Make it return something more usable.
    os.environ.setdefault("HOME", str(context.getFilesDir()))


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


def initialize_multiprocessing(context):
    # multiprocessing.dummy.Pool unnecessarily depends on multiprocessing.Lock, which requires
    # sem_open, which isn't available on Android. Work around this by replacing all the
    # multiprocessing primitives with their threading equivalents.
    import multiprocessing
    import threading

    # This needs to be wrapped in a function to capture the current value of `cls`.
    def make_method(name, cls):
        def method(self, *args, **kwargs):
            return cls(*args, **kwargs)
        method.__name__ = method.__qualname__ = name
        return method

    ctx_cls = type(multiprocessing.get_context())
    for name in ["Barrier", "BoundedSemaphore", "Condition", "Event", "Lock", "RLock",
                 "Semaphore"]:
        cls = getattr(threading, name)
        setattr(multiprocessing, name, cls)
        setattr(ctx_cls, name, make_method(name, cls))
