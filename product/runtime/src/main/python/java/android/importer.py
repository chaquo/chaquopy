import _imp
from calendar import timegm
import ctypes
from importlib import _bootstrap, _bootstrap_external, machinery, util
from inspect import getmodulename
import io
import os
from os.path import (
    basename, dirname, exists, isfile, join, normpath, realpath, relpath, split, splitext
)
from pathlib import Path
from pkgutil import get_importer
import re
from shutil import copyfileobj, rmtree
import site
import sys
from tempfile import NamedTemporaryFile
import time
from threading import RLock
from zipfile import ZipFile, ZipInfo
from zipimport import zipimporter

import java.chaquopy
from java._vendor.elftools.elf.elffile import ELFFile

from com.chaquo.python.android import AndroidPlatform
from com.chaquo.python.internal import Common


import_triggers = {}


def initialize(context, build_json, app_path):
    global nativeLibraryDir
    nativeLibraryDir = context.getApplicationInfo().nativeLibraryDir
    initialize_importlib(context, build_json, app_path)
    initialize_ctypes()
    if sys.version_info < (3, 12):
        initialize_imp()


def initialize_importlib(context, build_json, app_path):
    sys.meta_path[sys.meta_path.index(machinery.PathFinder)] = ChaquopyPathFinder

    # ZIP file extraction uses copyfileobj, whose default buffer size is 16 KB. This
    # significantly slows down ZipFile.extract with large files, because each call to
    # AssetFile.read has a relatively large overhead.
    assert len(copyfileobj.__defaults__) == 1
    copyfileobj.__defaults__ = (1024 * 1024,)

    # Use realpath to resolve any symlinks in getFilesDir(), otherwise there may be
    # confusion if user code derives a path from __file__, calls realpath on the result,
    # and then passes it back to us.
    global ASSET_PREFIX
    ASSET_PREFIX = join(realpath(context.getFilesDir().toString()),
                        Common.ASSET_DIR, "AssetFinder")

    def hook(path):
        return AssetFinder(context, build_json, path)
    sys.path_hooks.insert(0, hook)
    sys.path_hooks[sys.path_hooks.index(zipimporter)] = ChaquopyZipImporter
    sys.path_importer_cache.clear()

    sys.path = [p for p in sys.path if exists(p)]  # Remove nonexistent default paths
    for i, asset_name in enumerate(app_path):
        entry = join(ASSET_PREFIX, asset_name)
        sys.path.insert(i, entry)
        finder = get_importer(entry)
        assert isinstance(finder, AssetFinder), ("Finder for '{}' is {}"
                                                 .format(entry, type(finder).__name__))

        # Extract data files from the root directory. This includes .pth files, which will be
        # read by addsitedir below.
        finder.extract_dir("", recursive=False)

        # Extract data files from top-level directories which aren't Python packages.
        for name in finder.listdir(""):
            if finder.isdir(name) and \
               not is_dist_info(name) and \
               not any(finder.exists(f"{name}/__init__{suffix}") for suffix in LOADERS):
                finder.extract_dir(name)

        # We do this here instead of in AssetFinder.__init__ because code in the .pth files may
        # require the finder to be fully available to the system, which isn't the case until
        # get_importer returns.
        site.addsitedir(finder.extract_root)

    if sys.version_info[:2] == (3, 9):
        from importlib import _common
        global fallback_resources_original
        fallback_resources_original = _common.fallback_resources
        _common.fallback_resources = fallback_resources_39

    global spec_from_file_location_original
    spec_from_file_location_original = util.spec_from_file_location
    util.spec_from_file_location = spec_from_file_location_override


# Python 3.9 only supports importlib.resources.files for the standard importers.
def fallback_resources_39(spec):
    if isinstance(spec.loader, AssetLoader):
        return spec.loader.get_resource_reader(spec.name).files()
    else:
        return fallback_resources_original(spec)


def spec_from_file_location_override(name, location=None, *args, loader=None, **kwargs):
    if location and not loader:
        head, tail = split(location)
        tail = splitext(tail)[0]
        if tail == "__init__":
            head, tail = split(head)
        finder = get_importer(head)
        if isinstance(finder, AssetFinder):
            real_name = relpath(join(head, tail), finder.extract_root).replace("/", ".")
            spec = finder.find_spec(real_name)
            if spec:
                spec.name = name
                return spec

    return spec_from_file_location_original(name, location, *args, loader=loader, **kwargs)


def is_dist_info(name):
    return bool(re.search(r"\.(dist|egg)-info$", name))


def initialize_ctypes():
    import ctypes.util
    import sysconfig

    reqs_finder = get_importer(f"{ASSET_PREFIX}/requirements")

    # The standard implementation of find_library requires external tools, so will always fail
    # on Android.
    def find_library_override(name):
        filename = "lib{}.so".format(name)

        # First look in the requirements. The return value will probably be passed to
        # CDLL_init_override below, but the caller may load the library using another
        # API (e.g. soundfile uses ffi.dlopen), so make sure its dependencies are
        # extracted and pre-loaded.
        try:
            return reqs_finder.extract_lib(filename)
        except FileNotFoundError:
            pass

        # For system libraries I can't see any easy way of finding the absolute library
        # filename, but we can at least support the case where the user passes the return value
        # of find_library to CDLL().
        try:
            ctypes.CDLL(filename)
            return filename
        except OSError:
            return None

    ctypes.util.find_library = find_library_override

    def CDLL_init_override(self, name, *args, **kwargs):
        if name:  # CDLL(None) is equivalent to dlopen(NULL).
            if "/" not in name:
                try:
                    name = reqs_finder.extract_lib(name)
                except FileNotFoundError:
                    pass
            else:
                # Some packages (e.g. llvmlite) use CDLL to load libraries from their own
                # directories.
                finder = get_importer(dirname(name))
                if isinstance(finder, AssetFinder):
                    name = finder.extract_so(name)

        CDLL_init_original(self, name, *args, **kwargs)

    CDLL_init_original = ctypes.CDLL.__init__
    ctypes.CDLL.__init__ = CDLL_init_override

    # The standard library initializes pythonapi to PyDLL(None), because libpython is
    # statically linked to the executable in a normal Linux environment.
    ctypes.pythonapi = ctypes.PyDLL(sysconfig.get_config_vars()["LDLIBRARY"])


def initialize_imp():
    import imp

    # The standard implementations of imp.find_module and imp.load_module do not use the PEP
    # 302 import system. They are therefore only capable of loading from directory trees and
    # built-in modules, and will ignore both sys.path_hooks and sys.meta_path. To accommodate
    # code which uses these functions, we provide these replacements.
    global find_module_original, load_module_original
    find_module_original = imp.find_module
    load_module_original = imp.load_module
    imp.find_module = find_module_override
    imp.load_module = load_module_override


def find_module_override(base_name, path=None):
    import imp

    # When calling find_module_original, we can't just replace None with sys.path, because None
    # will also search built-in modules.
    path_original = path

    if path is None:
        path = sys.path
    for entry in path:
        finder = get_importer(entry)
        if hasattr(finder, "prefix"):  # AssetFinder or zipimporter
            real_name = join(finder.prefix, base_name).replace("/", ".")
            loader = finder.find_module(real_name)
            if loader is not None:
                filename = loader.get_filename(real_name)
                if loader.is_package(real_name):
                    file = None
                    pathname = dirname(filename)
                    suffix, mode, mod_type = ("", "", imp.PKG_DIRECTORY)
                else:
                    for suffix, mode, mod_type in imp.get_suffixes():
                        if filename.endswith(suffix):
                            break
                    else:
                        raise ValueError("Couldn't determine type of module '{}' from '{}'"
                                         .format(real_name, filename))

                    # SWIG-generated code such as
                    # tensorflow_core/python/pywrap_tensorflow_internal.py requires the file
                    # object to be not None, so we'll return an object of the correct type.
                    # However, we won't bother to supply the data, because the file may be as
                    # large as 200 MB in the case of tensorflow, which would reduce performance
                    # unnecessarily and maybe even exhaust the device's memory.
                    file = io.BytesIO() if mode == "rb" else io.StringIO()
                    pathname = filename

                if mod_type == imp.C_EXTENSION:
                    # torchvision/extension.py uses imp.find_module to find a non-Python .so
                    # file, which it then loads using CDLL. So we need to extract the file now.
                    finder.extract_if_changed(finder.zip_path(pathname))

                return (file, pathname, (suffix, mode, mod_type))

    return find_module_original(base_name, path_original)


def load_module_override(load_name, file, pathname, description):
    if pathname is not None:
        finder = get_importer(dirname(pathname))
        if hasattr(finder, "prefix"):  # AssetFinder or zipimporter
            entry, base_name = split(pathname)
            real_name = join(finder.prefix, splitext(base_name)[0]).replace("/", ".")
            if isinstance(finder, AssetFinder):
                spec = finder.find_spec(real_name)
                spec.name = load_name
                return _bootstrap._load(spec)
            elif real_name == load_name:
                return finder.find_module(real_name).load_module(real_name)
            else:
                raise ImportError(
                    "{} does not support loading module '{}' under a different name '{}'"
                    .format(type(finder).__name__, real_name, load_name))

    return load_module_original(load_name, file, pathname, description)


# Because so much code requires pkg_resources without declaring setuptools as a dependency, we
# include it in the bootstrap ZIP. We don't include the rest of setuptools, because it's much
# larger and much less likely to be useful. If the user installs setuptools via pip, then that
# copy of pkg_resources will take priority because the requirements ZIP is earlier on sys.path.
#
# pkg_resources is quite large, so this function shouldn't be called until the app needs it.
def initialize_pkg_resources():
    import pkg_resources

    def distribution_finder(finder, entry, only):
        for name in finder.listdir(""):
            if is_dist_info(name):
                yield pkg_resources.Distribution.from_location(entry, name)

    pkg_resources.register_finder(AssetFinder, distribution_finder)
    pkg_resources.working_set = pkg_resources.WorkingSet()

    class AssetProvider(pkg_resources.NullProvider):
        def __init__(self, module):
            super().__init__(module)
            self.finder = self.loader.finder

        # pkg_resources has a mechanism for extracting resources to temporary files, but
        # we don't currently support it. So this will only work for files which are
        # already extracted.
        def get_resource_filename(self, manager, resource_name):
            path = self._fn(self.module_path, resource_name)
            if not self._has(path):
                raise FileNotFoundError(path)
            return path

        def _has(self, path):
            return self.finder.exists(self.finder.zip_path(path))

        def _isdir(self, path):
            return self.finder.isdir(self.finder.zip_path(path))

        def _listdir(self, path):
            return self.finder.listdir(self.finder.zip_path(path))

    pkg_resources.register_loader_type(AssetLoader, AssetProvider)


# Patch old versions of zipimporter to provide the new loader API, which is required by
# dateparser (https://stackoverflow.com/q/63574951). Once our minimum Python version is
# 3.10 or higher, this should be removed.
for name in ["create_module", "exec_module"]:
    if not hasattr(zipimporter, name):
        setattr(zipimporter, name, getattr(_bootstrap_external._LoaderBasics, name))

# For consistency with modules which have already been imported by the default zipimporter, we
# retain the following default behaviours:
#   * __file__ will end with ".pyc", not ".py"
#   * co_filename will be taken from the .pycs in the ZIP, which means it'll start with
#    "stdlib/" or "bootstrap/".
class ChaquopyZipImporter(zipimporter):

    def exec_module(self, mod):
        super().exec_module(mod)
        exec_module_trigger(mod)

    def __repr__(self):
        return f'<{type(self).__name__} object "{join(self.archive, self.prefix)}">'


# importlib.metadata is still being actively developed, so instead of depending on any internal
# APIs, provide a self-contained implementation.
class ChaquopyPathFinder(machinery.PathFinder):
    @classmethod
    def find_distributions(cls, context=None):
        # importlib.metadata and its dependencies are quite large, and it won't be used in
        # most apps, so don't import it until it's needed.
        from importlib import metadata

        if context is None:
            context = metadata.DistributionFinder.Context()
        name = (".*" if context.name is None
                # See normalize_name_wheel in build-wheel.py.
                else re.sub(r"[^A-Za-z0-9.]+", '_', context.name))
        pattern = fr"^{name}(-.*)?\.(dist|egg)-info$"

        for entry in context.path:
            path_cls = AssetPath if entry.startswith(ASSET_PREFIX + "/") else Path
            entry_path = path_cls(entry)
            try:
                if entry_path.is_dir():
                    for sub_path in entry_path.iterdir():
                        if re.search(pattern, sub_path.name, re.IGNORECASE):
                            yield metadata.PathDistribution(sub_path)
            except PermissionError:
                pass  # Inaccessible path entries should be ignored.


# This does not inherit from PosixPath, because that would cause
# importlib.resources.as_file to return it unchanged, rather than creating a temporary
# file as it should. However, once our minimum version is Python 3.9, we can inherit
# from importlib.resources.abc.Traversable, and remove our implementations of read_text,
# read_bytes, and __truediv__.
class AssetPath:
    def __init__(self, path):
        root_dir = path
        while dirname(root_dir) != ASSET_PREFIX:
            root_dir = dirname(root_dir)
            assert root_dir, path
        self.finder = get_importer(root_dir)
        self.zip_path = self.finder.zip_path(path)

    def __str__(self):
        return join(self.finder.extract_root, self.zip_path)

    def __repr__(self):
        return f"{type(self).__name__}({str(self)!r})"

    def __eq__(self, other):
        return (type(self) is type(other)) and (str(self) == str(other))

    def __hash(self):
        return hash(str(self))

    @property
    def name(self):
        return basename(str(self))

    def exists(self):
        return self.finder.exists(self.zip_path)

    def is_dir(self):
        return self.finder.isdir(self.zip_path)

    def is_file(self):
        return self.exists() and not self.is_dir()

    def iterdir(self):
        for name in self.finder.listdir(self.zip_path):
            yield self.joinpath(name)

    def joinpath(self, *segments):
        child_path = join(str(self), *segments)
        if isfile(child_path):
            return Path(child_path)  # For data files created by extract_dir.
        else:
            return type(self)(child_path)

    def __truediv__(self, child):
        return self.joinpath(child)

    # `buffering` has no effect because the whole file is read immediately.
    def open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        if "r" in mode:
            bio = io.BytesIO(self.finder.get_data(self.zip_path))
            if mode == "r":
                return io.TextIOWrapper(bio, encoding, errors, newline)
            elif sorted(mode) == ["b", "r"]:
                return bio
        raise ValueError(f"unsupported mode: {mode!r}")

    def read_bytes(self):
        with self.open('rb') as strm:
            return strm.read()

    def read_text(self, encoding=None, errors=None, newline=None):
        with self.open("r", -1, encoding, errors, newline) as strm:
            return strm.read()


class AssetFinder:
    def __init__(self, context, build_json, path):
        if not path.startswith(ASSET_PREFIX + "/"):
            raise ImportError(f"not an asset path: '{path}'")
        self.context = context  # Also used in tests.
        self.path = path

        parent_path = dirname(path)
        if parent_path == ASSET_PREFIX:  # Root finder
            self.extract_root = path
            self.prefix = ""
            sp = context.getSharedPreferences(Common.ASSET_DIR, context.MODE_PRIVATE)
            assets_json = build_json["assets"]
            self.extract_packages = build_json["extract_packages"]

            # To allow modules in both requirements ZIPs to access data files from the other
            # ZIP, we extract both ZIPs to the same directory, and make both ZIPs generate
            # modules whose __file__ and __path__ point to that directory. This is most easily
            # done by accessing both ZIPs through the same finder.
            self.zip_files = []
            for abi in [None, Common.ABI_COMMON, AndroidPlatform.ABI]:
                asset_name = Common.assetZip(basename(self.extract_root), abi)
                try:
                    self.zip_files.append(
                        AssetZipFile(self.context, join(Common.ASSET_DIR, asset_name)))
                except FileNotFoundError:
                    continue

                # See also similar code in AndroidPlatform.java.
                sp_key = "asset." + asset_name
                new_hash = assets_json[asset_name]
                if sp.getString(sp_key, "") != new_hash:
                    if exists(self.extract_root):
                        rmtree(self.extract_root)
                    sp.edit().putString(sp_key, new_hash).apply()

            if not self.zip_files:
                raise FileNotFoundError(path)

            # Affects site.addsitedir which is called above (see site._init_pathinfo).
            os.makedirs(self.extract_root, exist_ok=True)
        else:
            parent = get_importer(parent_path)
            self.extract_root = parent.extract_root
            self.prefix = relpath(path, self.extract_root)
            self.zip_files = parent.zip_files
            self.extract_packages = parent.extract_packages

    def __repr__(self):
        return f"{type(self).__name__}({self.path!r})"

    def find_spec(self, mod_name, target=None):
        spec = None
        loader = self.find_module(mod_name)
        if loader:
            spec = util.spec_from_loader(mod_name, loader)
        else:
            dir_path = join(self.prefix, mod_name.rpartition(".")[2])
            if self.isdir(dir_path):
                # Possible namespace package.
                spec = machinery.ModuleSpec(mod_name, None)
                spec.submodule_search_locations = [join(self.extract_root, dir_path)]
        return spec

    def find_module(self, mod_name):
        # Ignore all but the last word of the name (see FileFinder.find_spec).
        prefix = join(self.prefix, mod_name.rpartition(".")[2])
        # Packages take priority over modules (see FileFinder.find_spec).
        for infix in ["/__init__", ""]:
            for zf in self.zip_files:
                for suffix, loader_cls in LOADERS.items():
                    try:
                        zip_info = zf.getinfo(prefix + infix + suffix)
                    except KeyError:
                        continue
                    if (infix == "/__init__") and ("." not in mod_name):
                        # This is a top-level package: extract all data files within it.
                        self.extract_dir(prefix)
                    return loader_cls(self, mod_name, zip_info)
        return None

    # Called by pkgutil.iter_modules.
    def iter_modules(self, prefix=""):
        try:
            filenames = self.listdir(self.prefix)
        except OSError:
            # ignore unreadable directories like import does
            filenames = []

        for filename in filenames:
            zip_path = join(self.prefix, filename)
            if self.isdir(zip_path):
                for sub_filename in self.listdir(zip_path):
                    if getmodulename(sub_filename) == "__init__":
                        yield prefix + filename, True
                        break
            else:
                mod_base_name = getmodulename(filename)
                if mod_base_name and (mod_base_name != "__init__"):
                    yield prefix + mod_base_name, False

    # If this method raises FileNotFoundError, then maybe it's a system library, or one of the
    # libraries loaded by AndroidPlatform.loadNativeLibs. If the library is truly missing,
    # we'll get an exception when we load the file that needs it.
    def extract_lib(self, filename):
        return self.extract_so(f"chaquopy/lib/{filename}")

    def extract_so(self, path):
        path = self.extract_if_changed(self.zip_path(path))
        load_needed(self, path)
        return path

    def extract_dir(self, zip_dir, recursive=True):
        dotted_dir = zip_dir.replace("/", ".")
        extract_package = any((dotted_dir == ep) or dotted_dir.startswith(ep + ".")
                              for ep in self.extract_packages)

        for filename in self.listdir(zip_dir):
            zip_path = join(zip_dir, filename)
            if self.isdir(zip_path):
                if recursive:
                    self.extract_dir(zip_path)
            elif (extract_package and filename.endswith(".py")
                  or not (any(filename.endswith(suffix) for suffix in LOADERS) or
                          re.search(r"^lib.*\.so\.", filename))):  # e.g. libgfortran
                self.extract_if_changed(zip_path)

    def extract_if_changed(self, zip_path):
        # Unlike AssetZipFile.extract_if_changed, this method may search multiple ZIP files, so
        # it can't take a ZipInfo argument.
        assert isinstance(zip_path, str)

        for zf in self.zip_files:
            try:
                return zf.extract_if_changed(zip_path, self.extract_root)
            except KeyError:
                pass
        raise FileNotFoundError(zip_path)

    def exists(self, zip_path):
        return any(zf.exists(zip_path) for zf in self.zip_files)

    def isdir(self, zip_path):
        return any(zf.isdir(zip_path) for zf in self.zip_files)

    def listdir(self, zip_path):
        result = [name for zf in self.zip_files if zf.isdir(zip_path)
                  for name in zf.listdir(zip_path)]
        if not result and not self.isdir(zip_path):
            raise (NotADirectoryError if self.exists(zip_path) else FileNotFoundError)(zip_path)
        return result

    def get_data(self, zip_path):
        for zf in self.zip_files:
            if zf.isdir(zip_path):
                raise IsADirectoryError(zip_path)
            try:
                return zf.read(zip_path)
            except KeyError:
                pass
        raise FileNotFoundError(zip_path)

    def zip_path(self, path):
        # If `path` is absolute then `join` will return it unchanged.
        path = join(self.extract_root, path)
        if path == self.extract_root:
            return ""
        if not path.startswith(self.extract_root + "/"):
            raise ValueError(f"{self} can't access '{path}'")
        return path[len(self.extract_root) + 1:]


# To create a concrete loader class, inherit this class followed by a FileLoader
# subclass, in that order.
class AssetLoader:
    def __init__(self, finder, fullname, zip_info):
        self.finder = finder
        self.zip_info = zip_info
        super().__init__(fullname, join(finder.extract_root, zip_info.filename))

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r}, {self.path!r})"

    # Override to disable the fullname check. This is only necessary for module renaming
    # via `imp`, so it can be removed one our minimum version is Python 3.12.
    def get_filename(self, fullname):
        return self.path

    def get_data(self, path):
        if exists(path):
            # For __pycache__ directories created by SourceAssetLoader, and data files created
            # by extract_dir.
            with open(path, "rb") as f:
                return f.read()
        return self.finder.get_data(self.finder.zip_path(path))

    def exec_module(self, mod):
        super().exec_module(mod)
        exec_module_trigger(mod)

    # The importlib.resources.abc documentation says "If the module specified by
    # fullname is not a package, this method should return None", but that's no longer
    # true as of Python 3.12, because importlib.resources.files can accept a module as
    # well as a package.
    def get_resource_reader(self, fullname):
        assert fullname == self.name, (fullname, self.name)
        return AssetResourceReader(self.finder, dirname(self.path))


class AssetResourceReader:
    def __init__(self, finder, path):
        assert finder.isdir(finder.zip_path(path)), path
        self.asset_path = AssetPath(path)

    def __repr__(self):
        return f"<{type(self).__name__} {str(self.asset_path)!r}>"

    # Implementation of importlib.resources.abc.TraversableResources
    def files(self):
        return self.asset_path

    # The remaining methods are an implementation of
    # importlib.resources.abc.ResourceReader. In Python 3.11, the old
    # importlib.resources API is entirely implemented in terms of the new API, so once
    # that's our minimum version, we can remove these methods and inherit them from
    # TraversableResources instead.

    def open_resource(self, resource):
        return self.files().joinpath(resource).open('rb')

    def resource_path(self, resource):
        path = self.files().joinpath(resource)
        if isinstance(path, Path):
            return path  # For data files created by extract_dir.
        else:
            # importlib.resources.path will call open_resource and create a temporary file.
            raise FileNotFoundError()

    # The documentation says this should raise FileNotFoundError if the name doesn't
    # exist, but that would cause inconsistent behavior of the public is_resource
    # function, which forwards directly to this method before Python 3.11, but uses
    # files().iterdir() after Python 3.11.
    def is_resource(self, name):
        return self.files().joinpath(name).is_file()

    def contents(self):
        return (item.name for item in self.files().iterdir())


def add_import_trigger(name, trigger):
    """Register a callable to be called immediately after the module of the given name
    is imported. If the module has already been imported, the trigger is called
    immediately."""

    if name in sys.modules:
        trigger()
    else:
        import_triggers[name] = trigger


def exec_module_trigger(mod):
    name = mod.__name__
    if name == "pkg_resources":
        initialize_pkg_resources()
    elif name == "numpy":
        java.chaquopy.numpy = mod  # See conversion.pxi.
    else:
        trigger = import_triggers.pop(name, None)
        if trigger:
            trigger()


# The SourceFileLoader base class will automatically create and use _pycache__ directories.
class SourceAssetLoader(AssetLoader, machinery.SourceFileLoader):
    def path_stats(self, path):
        return {"mtime": timegm(self.zip_info.date_time),
                "size": self.zip_info.file_size}


# In case user code depends on the original source filename, we make sure it's used in
# __file__ and in tracebacks.
class SourcelessAssetLoader(AssetLoader, machinery.SourcelessFileLoader):
    def exec_module(self, mod):
        assert self.path.endswith(".pyc"), self.path
        mod.__file__ = self.path[:-1]
        return super().exec_module(mod)

    def get_code(self, fullname):
        code = super().get_code(fullname)
        _imp._fix_co_filename(code, self.path[:-1])
        return code


class ExtensionAssetLoader(AssetLoader, machinery.ExtensionFileLoader):
    def create_module(self, spec):
        self.finder.extract_so(self.path)
        return super().create_module(spec)


needed_lock = RLock()
needed_loaded = {}

# CDLL will cause a recursive call back to extract_so, so there's no need for any additional
# recursion here. If we return to executables in the future, we can implement a separate
# recursive extraction on top of get_needed.
def load_needed(finder, path):
    with needed_lock:
        for soname in get_needed(path):
            if soname not in needed_loaded:
                try:
                    # Before API level 23, the only dlopen mode was RTLD_GLOBAL, and
                    # RTLD_LOCAL was ignored. From API level 23, RTLD_LOCAL is available
                    # and used by default, just like in Linux
                    # (https://android.googlesource.com/platform/bionic/+/master/android-changes-for-ndk-developers.md).
                    #
                    # We use RTLD_GLOBAL to make the library's symbols available to
                    # subsequently-loaded libraries, but this may not actually work -
                    # see #728.
                    #
                    # It doesn't look like the library is closed when the CDLL object is garbage
                    # collected, but this isn't documented, so keep a reference for safety.
                    needed_loaded[soname] = ctypes.CDLL(soname, ctypes.RTLD_GLOBAL)
                except FileNotFoundError:
                    needed_loaded[soname] = None


def get_needed(path):
    with open(path, "rb") as file:
        ef = ELFFile(file)
        dynamic = ef.get_section_by_name(".dynamic")
        if dynamic:
            return [tag.needed for tag in dynamic.iter_tags()
                    if tag.entry.d_tag == "DT_NEEDED"]
        else:
            return []


# If a module has both a .py and a .pyc file, the .pyc file should be used because
# it'll load faster.
LOADERS = {
    ".pyc": SourcelessAssetLoader,
    ".py": SourceAssetLoader,
    ".so": ExtensionAssetLoader,
}


class AssetZipFile(ZipFile):
    def __init__(self, context, path, *args, **kwargs):
        super().__init__(java.chaquopy.AssetFile(context, path), *args, **kwargs)

        self.dir_index = {"": set()}  # Provide empty listing for root even if ZIP is empty.
        for name in self.namelist():
            # If `name` ends with a slash, it represents a directory. However, not all ZIP
            # files contain these entries.
            parts = name.split("/")
            while parts:
                parent = "/".join(parts[:-1])
                if parent in self.dir_index:
                    self.dir_index[parent].add(parts[-1])
                    break
                else:
                    base_name = parts.pop()
                    self.dir_index[parent] = set([base_name] if base_name else [])
        self.dir_index = {k: sorted(v) for k, v in self.dir_index.items()}

    # Based on ZipFile.extract, but fixed to be safe in the presence of multiple threads
    # creating the same file or directory.
    def extract(self, member, target_dir):
        if not isinstance(member, ZipInfo):
            member = self.getinfo(member)

        out_filename = normpath(join(target_dir, member.filename))
        out_dirname = dirname(out_filename)
        if out_dirname:
            os.makedirs(out_dirname, exist_ok=True)

        if member.is_dir():
            os.makedirs(out_filename, exist_ok=True)
        else:
            with self.open(member) as source_file, \
                 NamedTemporaryFile(delete=False, dir=out_dirname,
                                    prefix=basename(out_filename) + ".") as tmp_file:
                copyfileobj(source_file, tmp_file)
            os.replace(tmp_file.name, out_filename)

        return out_filename

    # ZipFile.extract does not set any metadata (https://bugs.python.org/issue32170), so we set
    # the timestamp after extraction is complete. That way, if the app gets killed in the
    # middle of an extraction, the timestamps won't match and we'll know we need to extract the
    # file again.
    #
    # The Gradle plugin sets all ZIP timestamps to 1980 for reproducibility, so we can't rely
    # on them to tell us which files have changed after an app update. Instead,
    # AssetFinder.__init__ just removes the whole extract_root if any of its ZIPs have changed.
    def extract_if_changed(self, member, target_dir):
        if not isinstance(member, ZipInfo):
            member = self.getinfo(member)

        need_extract = True
        out_filename = join(target_dir, member.filename)
        if exists(out_filename):
            existing_stat = os.stat(out_filename)
            need_extract = (existing_stat.st_size != member.file_size or
                            existing_stat.st_mtime != timegm(member.date_time))

        if need_extract:
            extracted_filename = self.extract(member, target_dir)
            assert extracted_filename == out_filename, (extracted_filename, out_filename)
            os.utime(out_filename, (time.time(), timegm(member.date_time)))
        return out_filename

    def exists(self, path):
        if self.isdir(path):
            return True
        try:
            self.getinfo(path)
            return True
        except KeyError:
            return False

    def isdir(self, path):
        return path.rstrip("/") in self.dir_index

    def listdir(self, path):
        return self.dir_index[path.rstrip("/")]
