"""Copyright (c) 2017 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

from calendar import timegm
from functools import partial
import imp
import io
import marshal
import os
from os.path import basename, dirname, exists, join
import re
import struct
import sys
import time
from threading import RLock
from traceback import format_exc
from types import ModuleType
from zipfile import ZipFile

from android.content.res import AssetManager
from android.os import Build
from com.chaquo.python import Common
from java import jarray, jbyte
from java.lang import Integer
from java._vendor import six

if six.PY3:
    from tokenize import detect_encoding


def initialize(context, app_path):
    sys.path_hooks.insert(0, partial(AssetFinder, context))
    for i, path in enumerate(app_path):
        sys.path.insert(i, join("/android_asset", Common.ASSET_DIR, path))


class AssetFinder(object):
    def __init__(self, context, path):
        try:
            self.context = context
            self.path = path
            self.zip_file = ZipFile(AssetFile(context.getAssets(), path))
            self.extract_root = join(context.getCacheDir().toString(), Common.ASSET_DIR,
                                     "AssetFinder", basename(path))
            self.lock = RLock()

        # If we raise ImportError, the finder is silently skipped. This is what we want only if
        # the path entry isn't an asset path: all other errors should abort the import,
        # including when the asset doesn't exist.
        except InvalidAssetPathError:
            raise ImportError(format_exc())
        except ImportError:
            raise Exception(format_exc())

    def find_module(self, mod_name):
        prefix = mod_name.replace(".", "/")
        # Packages take priority over modules (https://stackoverflow.com/questions/4092395/)
        for infix in ["/__init__", ""]:
            for suffix, loader in LOADERS:
                try:
                    zip_info = self.zip_file.getinfo(prefix + infix + suffix)
                except KeyError:
                    continue
                return loader(self, mod_name, zip_info)


class AssetLoader(object):
    def __init__(self, finder, mod_name, zip_info):
        self.finder = finder
        self.mod_name = mod_name
        self.zip_info = zip_info

    def load_module(self, mod_name):
        assert mod_name == self.mod_name
        is_reload = mod_name in sys.modules
        try:
            # Python guarantees that a given module will only be imported in one thread at a
            # time. And the ZipFile index is completely read during construction above, so
            # calling `getinfo` above is thread-safe. However, while actually reading files out
            # of the .zip, the AssetFile will be seeked, so we can only extract one file at a
            # time. Also, there's a race condition in makedirs below, so let's just serialize
            # at this level.
            with self.finder.lock:
                self.load_module_impl()
            # The module that ends up in sys.modules is not necessarily the one we just created
            # (e.g. see bottom of pygments/formatters/__init__.py).
            return sys.modules[mod_name]
        except Exception:
            if not is_reload:
                sys.modules.pop(mod_name, None)
            raise

    def set_mod_attrs(self, mod):
        mod.__name__ = self.mod_name  # Native module creation may set this to the unqualified name.
        mod.__file__ = self.get_filename(self.mod_name)
        if self.is_package(self.mod_name):
            mod.__package__ = self.mod_name
            mod.__path__ = [self.finder.path]
        else:
            mod.__package__ = self.mod_name.rpartition('.')[0]
        mod.__loader__ = self

    def get_data(self, path):
        match = re.search(r"^{}/(.+)$".format(self.finder.path), path)
        if not match:
            raise IOError("loader for '{}' can't access '{}'".format(self.finder.path, path))
        try:
            return self.finder.zip_file.read(match.group(1))
        except KeyError as e:
            raise IOError(str(e))

    def is_package(self, mod_name):
        assert mod_name == self.mod_name
        return basename(self.zip_info.filename).startswith("__init__.")

    def get_code(self, mod_name):
        assert mod_name == self.mod_name
        return None  # Not implemented

    # Overridden in SourceFileLoader
    def get_source(self, mod_name):
        assert mod_name == self.mod_name
        return None

    def get_filename(self, mod_name):
        assert mod_name == self.mod_name
        return join(self.finder.path, self.zip_info.filename)


# Irrespective of the Python version, we use the Python 3.6 .pyc layout (with size field).
PYC_HEADER_FORMAT = "<4siI"

class SourceFileLoader(AssetLoader):
    def load_module_impl(self):
        mod = sys.modules.get(self.mod_name)
        if mod is None:
            mod = ModuleType(self.mod_name)
            self.set_mod_attrs(mod)
            sys.modules[self.mod_name] = mod

        pyc_filename = join(self.finder.extract_root, self.zip_info.filename + "c")
        code = self.read_pyc(pyc_filename)
        if not code:
            # compile() doesn't impose the same restrictions as get_source().
            code = compile(self.get_source_bytes(), self.get_filename(self.mod_name), "exec",
                           dont_inherit=True)
            self.write_pyc(pyc_filename, code)
        six.exec_(code, mod.__dict__)

    # Should return a bytes string in Python 2, or a unicode string in Python 3, in both cases
    # with newlines normalized to "\n".
    def get_source(self, mod_name):
        assert mod_name == self.mod_name
        source_bytes = self.get_source_bytes()
        if six.PY2:
            # zipfile mode "rU" doesn't work with read() (https://bugs.python.org/issue6759),
            # and would probably have been slower than this anyway.
            return re.sub(r"\r\n?", "\n", source_bytes)
        else:
            # Adapted from Python 3.6 importlib
            encoding, lines = detect_encoding(io.BytesIO(source_bytes).readline)
            return io.IncrementalNewlineDecoder(None, True).decode(
                source_bytes.decode(encoding))

    def get_source_bytes(self):
        return self.finder.zip_file.read(self.zip_info)

    def write_pyc(self, filename, code):
        pyc_dirname = dirname(filename)
        if not exists(pyc_dirname):
            os.makedirs(pyc_dirname)
        with open(filename, "wb") as pyc_file:
            # Write header last, so read_pyc doesn't try to load an incomplete file.
            header = self.pyc_header()
            pyc_file.seek(len(header))
            marshal.dump(code, pyc_file)
            pyc_file.seek(0)
            pyc_file.write(header)

    def read_pyc(self, filename):
        if not exists(filename):
            return None
        with open(filename, "rb") as pyc_file:
            expected_header = self.pyc_header()
            actual_header = pyc_file.read(len(expected_header))
            if actual_header != expected_header:
                return None
            try:
                return marshal.loads(pyc_file.read())
            except Exception:
                return None

    def pyc_header(self):
        return struct.pack(PYC_HEADER_FORMAT, imp.get_magic(), timegm(self.zip_info.date_time),
                           self.zip_info.file_size)


class ExtensionFileLoader(AssetLoader):
    def load_module_impl(self):
        if self.mod_name in sys.modules:
            raise ImportError("'{}': cannot reload a native module".format(self.mod_name))

        out_filename = join(self.finder.extract_root, self.zip_info.filename)
        if exists(out_filename):
            existing_stat = os.stat(out_filename)
            need_extract = (existing_stat.st_size != self.zip_info.file_size or
                            existing_stat.st_mtime != timegm(self.zip_info.date_time))
        else:
            need_extract = True
        if need_extract:
            self.finder.zip_file.extract(self.zip_info, self.finder.extract_root)
            os.utime(out_filename, (time.time(), timegm(self.zip_info.date_time)))

        mod = imp.load_dynamic(self.mod_name, out_filename)
        sys.modules[self.mod_name] = mod
        self.set_mod_attrs(mod)


SUPPORTED_ABIS = list(getattr(Build, "SUPPORTED_ABIS", [Build.CPU_ABI, Build.CPU_ABI2]))
for abi in SUPPORTED_ABIS:
    if abi in Common.ABIS.toArray():
        break
else:
    raise Exception("couldn't identify ABI: supported={}".format(SUPPORTED_ABIS))

# These class names are based on the standard Python 3 loaders from importlib.machinery, though
# their interfaces are somewhat different.
LOADERS = [
    (".py", SourceFileLoader),
    (".{}.so".format(abi), ExtensionFileLoader),    # For requirements.zip
    (".so".format(abi), ExtensionFileLoader),       # For stdlib-native/<abi>.zip
    # No current need for a SourcelessFileLoader, since we exclude .pyc files from app.zip and
    # requirements.zip. To support this fully for both Python 2 and 3 would be non-trivial due
    # to the variation in bytecode file names and locations. However, we could select one
    # variation and use it for all Python versions.
]


class AssetFile(object):
    def __init__(self, asset_manager, path):
        match = re.search(r"^/android_asset/(.+)$", path)
        if not match:
            raise InvalidAssetPathError("not an android_asset path: '{}'".format(path))
        self.name = path
        self.stream = asset_manager.open(match.group(1), AssetManager.ACCESS_RANDOM)
        self.stream.mark(Integer.MAX_VALUE)
        self.offset = 0
        self.length = self.stream.available()

    def read(self, size=None):
        if size is None:
            size = self.stream.available()
        array = jarray(jbyte)(size)
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
        return offset   # Required in Python 3: Python 2 returns None.

    def tell(self):
        return self.offset

    def close(self):
        self.stream.close()
        self.stream = None


class InvalidAssetPathError(ValueError):
    pass
