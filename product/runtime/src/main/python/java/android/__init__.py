import os
from os.path import join
import sys
import traceback
from types import ModuleType
import warnings
from . import importer

from org.json import JSONArray, JSONObject


def initialize(context_local, build_json_object, app_path):
    global context
    context = context_local

    # Redirect stdout and stderr to logcat - this was upstreamed in Python 3.13.
    if sys.version_info < (3, 13):
        from ctypes import CDLL, c_char_p, c_int
        from . import stream

        android_log_write = getattr(CDLL("liblog.so"), "__android_log_write")
        android_log_write.argtypes = (c_int, c_char_p, c_char_p)
        stream.init_streams(android_log_write, stdout_prio=4, stderr_prio=5)
    elif sys.stdout.errors == "backslashreplace":
        # This fix should be upstreamed in Python 3.13.1.
        raise Exception("see if sys.stdout.errors workaround can be removed")
    else:
        sys.stdout.reconfigure(errors="backslashreplace")

    importer.initialize(context, convert_json_object(build_json_object), app_path)

    # These are ordered roughly from low to high level.
    for name in [
        "warnings", "sys", "os", "tempfile", "ssl", "multiprocessing"
    ]:
        importer.add_import_trigger(name, globals()[f"initialize_{name}"])


def convert_json_object(obj):
    if isinstance(obj, JSONObject):
        result = {}
        i_keys = obj.keys()
        while i_keys.hasNext():
            key = i_keys.next()
            result[key] = convert_json_object(obj.get(key))
    elif isinstance(obj, JSONArray):
        result = [convert_json_object(obj.get(i))
                  for i in range(obj.length())]
    else:
        assert isinstance(obj, (type(None), bool, int, float, str)), obj
        result = obj
    return result


# Several warning classes are ignored by default to avoid confusing end-users. But on
# Android warnings are printed to the logcat, which is only visible to developers.
def initialize_warnings():
    warnings.resetwarnings()


def initialize_sys():
    # executable defaults to the empty string, but this causes platform.platform() to
    # crash, and would probably confuse a lot of other code as well.
    try:
        sys.executable = os.readlink("/proc/{}/exe".format(os.getpid()))
    except Exception:
        # Can't be certain that /proc will work on all devices, so try to carry on.
        traceback.print_exc()
        sys.executable = ""


def initialize_os():
    import errno

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

    # Our redirectStdioToLogcat mechanism replaces the native stdout with a pipe, so
    # attempting to get its terminal size returns EPERM rather than ENOTTY. Both of
    # these result in an OSError, so the calling code will still work, but it generates
    # a log message like `avc: denied { ioctl } for path="pipe:[10138300]"`, which can
    # be a problem if the app is doing it repeatedly.
    def get_terminal_size_override(*args, **kwargs):
        error = errno.ENOTTY
        raise OSError(error, os.strerror(error))
    os.get_terminal_size = get_terminal_size_override


def initialize_tempfile():
    tmpdir = join(str(context.getCacheDir()), "chaquopy/tmp")
    os.makedirs(tmpdir, exist_ok=True)
    os.environ["TMPDIR"] = tmpdir


def initialize_ssl():
    # OpenSSL may be able to find the system CA store on some devices, but for consistency
    # we disable this and use our own bundled file.
    #
    # Unfortunately we can't do this with SSL_CERT_FILE, because OpenSSL ignores
    # environment variables when getauxval(AT_SECURE) is enabled, which is always the case
    # on Android (https://android.googlesource.com/platform/bionic/+/6bb01b6%5E%21/).
    #
    # TODO: to pass the CPython test suite, we have now patched our OpenSSL build to
    # ignore AT_SECURE, so we can probably use the environment variable now.
    import ssl
    cacert = join(str(context.getFilesDir()), "chaquopy/cacert.pem")
    def set_default_verify_paths(self):
        self.load_verify_locations(cacert)
    ssl.SSLContext.set_default_verify_paths = set_default_verify_paths


def initialize_multiprocessing():
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
        # multiprocessing.synchronize reads this attribute during import.
        SEM_VALUE_MAX = 99

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
