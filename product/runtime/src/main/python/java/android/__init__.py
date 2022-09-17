import os
from os.path import join
import sys
import traceback
from types import ModuleType
from . import stream, importer


def initialize(context_local, build_json, app_path):
    global context
    context = context_local

    stream.initialize()
    importer.initialize(context, build_json, app_path)

    # These are ordered roughly from low to high level.
    for name in ["sys", "os", "tempfile", "multiprocessing"]:
        globals()[f"initialize_{name}"]()


def initialize_sys():
    # argv defaults to not existing, which may crash some programs.
    sys.argv = [""]

    # executable defaults to the empty string, but this causes platform.platform() to crash.
    try:
        sys.executable = os.readlink("/proc/{}/exe".format(os.getpid()))
    except Exception:
        # Can't be certain that /proc will work on all devices, so try to carry on.
        traceback.print_exc()
        sys.executable = ""


def initialize_os():
    # By default, os.path.expanduser("~") returns "/data", which is an unwritable directory.
    # Make it return something more usable.
    os.environ.setdefault("HOME", str(context.getFilesDir()))

    # Many devices include inaccessible directories on the PATH. This may cause subprocess.run
    # to raise a PermissionError when passed a nonexistent executable, rather than the
    # FileNotFoundError which user code is probably expecting.
    def get_exec_path_override(*args, **kwargs):
        return [name for name in get_exec_path_original(*args, **kwargs)
                if os.access(name, os.X_OK)]  # Read permission is not required.
    get_exec_path_original = os.get_exec_path
    os.get_exec_path = get_exec_path_override


def initialize_tempfile():
    tmpdir = join(str(context.getCacheDir()), "chaquopy/tmp")
    os.makedirs(tmpdir, exist_ok=True)
    os.environ["TMPDIR"] = tmpdir


# Called from importer.exec_module_trigger.
def initialize_ssl():
    # OpenSSL may be able to find the system CA store on some devices, but for consistency
    # we disable this and use our own bundled file.
    #
    # Unfortunately we can't do this with SSL_CERT_FILE, because OpenSSL ignores
    # environment variables when getauxval(AT_SECURE) is enabled, which is always the case
    # on Android (https://android.googlesource.com/platform/bionic/+/6bb01b6%5E%21/).
    import ssl
    cacert = join(str(context.getFilesDir()), "chaquopy/cacert.pem")
    def set_default_verify_paths(self):
        self.load_verify_locations(cacert)
    ssl.SSLContext.set_default_verify_paths = set_default_verify_paths


def initialize_multiprocessing():
    import _multiprocessing
    from multiprocessing import context, heap, pool
    import threading

    # multiprocessing.dummy.Pool (aka multiprocessing.pool.ThreadPool) unnecessarily depends on
    # the multiprocessing synchronization primitives, which don't work on Android. Make it use
    # the threading primitives instead.
    def ThreadPool_init_override(self, *args, **kwargs):
        pool.Pool.__init__(self, *args, context=ThreadingContext(), **kwargs)
    pool.ThreadPool.__init__ = ThreadPool_init_override

    class ThreadingContext(context.BaseContext):
        pass

    # This needs to be wrapped in a function to capture the current value of `cls`.
    def make_method(name, cls):
        def method(self, *args, **kwargs):
            return cls(*args, **kwargs)
        method.__name__ = method.__qualname__ = name
        return method

    for name in ["Barrier", "BoundedSemaphore", "Condition", "Event", "Lock", "RLock",
                 "Semaphore"]:
        cls = getattr(threading, name)
        setattr(ThreadingContext, name, make_method(name, cls))

    # multiprocessing.synchronize throws an exception on import if the synchronization
    # primitives are unavailable. But this breaks some packages like librosa (via joblib and
    # loky) which import the primitives but don't always use them.
    #
    # So we defer the exception until one of the missing functions is actually used. If a user
    # encounters this with joblib, they can work around it by using the `parallel_backend`
    # context manager to select thread-based parallelism instead.
    try:
        import multiprocessing.synchronize  # noqa: F401
    except ImportError as e:
        error_message = str(e)
    else:
        raise Exception("multiprocessing.synchronize now imports successfully: check if its "
                        "workaround can be removed")

    class SemLock:
        SEM_VALUE_MAX = _multiprocessing.SemLock.SEM_VALUE_MAX
        def __init__(self, *args, **kwargs):
            raise OSError(error_message)

    def sem_unlink(*args, **kwargs):
        raise OSError(error_message)

    _mp_override = ModuleType("_multiprocessing")
    _mp_override.SemLock = SemLock
    _mp_override.sem_unlink = sem_unlink
    sys.modules["_multiprocessing"] = _mp_override

    # This attempts to access /dev/shm, which doesn't exist on Android.
    heap.Arena._dir_candidates = []
