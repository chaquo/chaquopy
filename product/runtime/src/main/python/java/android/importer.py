"""Copyright (c) 2019 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

from calendar import timegm
import ctypes
from functools import partial
import imp
from importlib import _bootstrap, machinery, util
from inspect import getmodulename
import io
import os.path
from os.path import basename, dirname, exists, join, relpath
from pkgutil import get_importer
from shutil import rmtree
import sys
import time
from threading import RLock
from traceback import format_exc
from zipfile import ZipFile, ZipInfo

from java._vendor.elftools.elf.elffile import ELFFile
from java.chaquopy import AssetFile

from com.chaquo.python import Common
from com.chaquo.python.android import AndroidPlatform


PATHNAME_PREFIX = "<chaquopy>/"


def initialize(context, build_json, app_path):
    initialize_importlib(context, build_json, app_path)
    initialize_imp()
    initialize_pkg_resources()


def initialize_importlib(context, build_json, app_path):
    # Remove nonexistent default paths (#5410)
    sys.path = [p for p in sys.path if exists(p)]

    global ASSET_PREFIX
    ASSET_PREFIX = join(context.getFilesDir().toString(), Common.ASSET_DIR, "AssetFinder")

    ep_json = build_json.get("extractPackages")
    extract_packages = set(ep_json.get(i) for i in range(ep_json.length()))
    sys.path_hooks.insert(0, partial(AssetFinder, context, extract_packages, build_json))

    for i, asset_name in enumerate(app_path):
        entry = join(ASSET_PREFIX, asset_name)
        sys.path.insert(i, entry)
        finder = get_importer(entry)
        assert isinstance(finder, AssetFinder), ("Finder for '{}' is {}"
                                                 .format(entry, type(finder).__name__))

        # FIXME: once .pth files are extracted during startup, replace this with a call to
        # site.addpackage immediately after that.
        sitedir = finder.path  # noqa: F841 (see note above)
        for pth_filename in finder.listdir("/"):
            if not pth_filename.endswith(".pth"):
                continue
            pth_content = finder.get_data(pth_filename).decode("UTF-8")
            for line_no, line in enumerate(pth_content.splitlines(), start=1):
                try:
                    line = line.strip()
                    if (not line) or line.startswith("#"):
                        pass
                    elif line.startswith(("import ", "import\t")):
                        exec(line, {})
                    else:
                        # We don't add anything to sys.path: there's no way it could possibly work.
                        pass
                except Exception:
                    print("Error processing line {} of {}/{}: {}"
                          .format(line_no, finder.path, pth_filename, format_exc()),
                          file=sys.stderr)
                    print("Remainder of file ignored", file=sys.stderr)
                    break


def initialize_imp():
    # The standard implementations of imp.{find,load}_module do not use the PEP 302 import
    # system. They are therefore only capable of loading from directory trees and built-in
    # modules, and will ignore both our path_hook and the standard one for zipimport. To
    # accommodate code which uses these functions, we provide these replacements.
    global find_module_original, load_module_original
    find_module_original = imp.find_module
    load_module_original = imp.load_module
    imp.find_module = find_module_override
    imp.load_module = load_module_override


# Unlike the other APIs in this file, find_module does not take names containing dots.
#
# The documentation says that if the module "does not live in a file", the returned tuple
# contains file=None and pathname="". However, the the only thing the user is likely to do with
# these values is pass them to load_module, so we should be safe to use them however we want:
#
#   * file=None causes problems for SWIG-generated code such as pywrap_tensorflow_internal, so
#     we return a dummy file-like object instead.
#
#   * `pathname` is used to communicate the location of the module to load_module_override.
def find_module_override(base_name, path=None):
    # When calling find_module_original, we can't just replace None with sys.path, because None
    # will also search built-in modules.
    path_original = path

    if path is None:
        path = sys.path
    for entry in path:
        finder = get_importer(entry)
        if finder is not None and \
           hasattr(finder, "prefix"):  # AssetFinder and zipimport both have this attribute.
            real_name = join(finder.prefix, base_name).replace("/", ".")
            loader = finder.find_module(real_name)
            if loader is not None:
                if loader.is_package(real_name):
                    file = None
                    mod_type = imp.PKG_DIRECTORY
                else:
                    file = io.BytesIO()
                    filename = loader.get_filename(real_name)
                    for suffix, mode, mod_type in imp.get_suffixes():
                        if filename.endswith(suffix):
                            break
                    else:
                        raise ValueError("Couldn't determine type of module '{}' from '{}'"
                                         .format(real_name, filename))

                return (file,
                        PATHNAME_PREFIX + join(entry, base_name),
                        ("", "", mod_type))

    return find_module_original(base_name, path_original)


def load_module_override(load_name, file, pathname, description):
    if (pathname is not None) and (pathname.startswith(PATHNAME_PREFIX)):
        entry, base_name = os.path.split(pathname[len(PATHNAME_PREFIX):])
        finder = get_importer(entry)
        real_name = join(finder.prefix, base_name).replace("/", ".")
        if hasattr(finder, "find_spec"):
            spec = finder.find_spec(real_name)
            spec.name = load_name
            return _bootstrap._load(spec)
        elif real_name == load_name:
            return finder.find_module(real_name).load_module(real_name)
        else:
            raise ImportError(
                "{} does not support loading module '{}' under a different name '{}'"
                .format(type(finder).__name__, real_name, load_name))
    else:
        return load_module_original(load_name, file, pathname, description)


def initialize_pkg_resources():
    # Because so much code requires pkg_resources without declaring setuptools as a dependency,
    # we include it in the bootstrap ZIP. We don't include the rest of setuptools, because it's
    # much larger and much less likely to be useful. If the user installs setuptools via pip,
    # then that copy of pkg_resources will take priority because the requirements ZIP is
    # earlier on sys.path.
    import pkg_resources

    def distribution_finder(finder, entry, only):
        for name in finder.listdir("/"):
            if name.endswith(".dist-info"):
                yield pkg_resources.Distribution.from_location(entry, name)

    pkg_resources.register_finder(AssetFinder, distribution_finder)
    pkg_resources.working_set = pkg_resources.WorkingSet()

    class AssetProvider(pkg_resources.NullProvider):
        def __init__(self, module):
            super().__init__(module)
            self.finder = self.loader.finder

        def _has(self, path):
            return self.finder.exists(self.finder.zip_path(path))

        def _isdir(self, path):
            return self.finder.isdir(self.finder.zip_path(path))

        def _listdir(self, path):
            return self.finder.listdir(self.finder.zip_path(path))

    pkg_resources.register_loader_type(AssetLoader, AssetProvider)


class AssetFinder:
    def __init__(self, context, extract_packages, build_json, path):
        if not path.startswith(ASSET_PREFIX + "/"):
            raise ImportError(f"not an asset path: '{path}'")

        self.context = context  # Also used in tests.
        self.extract_packages = extract_packages
        self.path = path

        sp = context.getSharedPreferences(Common.ASSET_DIR, context.MODE_PRIVATE)
        assets_json = build_json.get("assets")
        if dirname(path) == ASSET_PREFIX:  # Root finder
            self.extract_root = path
            self.prefix = ""

            # To allow modules in both requirements ZIPs to access data files from the other
            # ZIP, we extract both ZIPs to the same directory, and make both ZIPs generate
            # modules whose __file__ and __path__ point to that directory. This is most easily
            # done by accessing both ZIPs through the same finder.
            self.zip_files = []
            for suffix in [".zip", f"-{Common.ABI_COMMON}.zip", f"-{AndroidPlatform.ABI}.zip"]:
                asset_name = basename(self.extract_root) + suffix
                try:
                    self.zip_files.append(ConcurrentZipFile(
                        AssetFile(self.context, join(Common.ASSET_DIR, asset_name))))
                except FileNotFoundError:
                    continue

                # See also similar code in AndroidPlatform.java.
                sp_key = "asset." + asset_name
                new_hash = assets_json.get(asset_name)
                if sp.getString(sp_key, "") != new_hash:
                    if exists(self.extract_root):
                        rmtree(self.extract_root)
                    sp.edit().putString(sp_key, new_hash).apply()

            if not self.zip_files:
                raise FileNotFoundError(path)
        else:
            parent = get_importer(dirname(path))
            self.extract_root = parent.extract_root
            self.prefix = relpath(path, self.extract_root)
            self.zip_files = parent.zip_files

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
                for suffix, loader_cls in LOADERS:
                    try:
                        zip_info = zf.getinfo(prefix + infix + suffix)
                    except KeyError:
                        continue
                    if infix == "/__init__" and mod_name in self.extract_packages:
                        self.extract_dir(prefix)
                    return loader_cls(self, mod_name, zip_info)
        return None

    # Called by pkgutil.iter_modules.
    def iter_modules(self, prefix=""):
        for filename in self.listdir(self.prefix):
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

    def extract_dir(self, zip_dir):
        for filename in self.listdir(zip_dir):
            zip_path = join(zip_dir, filename)
            if self.isdir(zip_path):
                self.extract_dir(zip_path)
            else:
                self.extract_if_changed(zip_path)

    def extract_if_changed(self, zip_path):
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
            try:
                return zf.read(zip_path)
            except KeyError:
                pass
        raise FileNotFoundError(zip_path)

    def zip_path(self, path):
        # If `path` is absolute then `join` will return it unchanged.
        path = join(self.extract_root, path)
        if not path.startswith(self.extract_root + "/"):
            raise ValueError(f"{self} can't access '{path}'")
        return path[len(self.extract_root) + 1:]


# To create a concrete loader class, inherit this class followed by a FileLoader subclass.
class AssetLoader:
    def __init__(self, finder, fullname, zip_info):
        self.finder = finder
        self.zip_info = zip_info
        super().__init__(fullname, join(finder.extract_root, zip_info.filename))

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r}, {self.path!r})"

    # Override to disable the fullname check. This is necessary for module renaming via imp.
    def get_filename(self, fullname):
        return self.path

    def get_data(self, path):
        if exists(path):  # For bytecode and pre-extracted files.
            with open(path, "rb") as f:
                return f.read()
        return self.finder.get_data(self.finder.zip_path(path))


# SourceFileLoader will access both the source and bytecode files via AssetLoader.get_data.
class SourceAssetLoader(AssetLoader, machinery.SourceFileLoader):
    def path_stats(self, path):
        return {"mtime": timegm(self.zip_info.date_time),
                "size": self.zip_info.file_size}


class ExtensionAssetLoader(AssetLoader, machinery.ExtensionFileLoader):
    needed_lock = RLock()
    needed_loaded = {}

    def create_module(self, spec):
        out_filename = self.extract_so()
        self.load_needed(out_filename)
        spec.origin = out_filename
        mod = super().create_module(spec)
        mod.__file__ = self.path  # In case user code depends on the original name.
        return mod

    # In API level 22 and older, when asked to load a library with the same basename as one
    # already loaded, the dynamic linker will return the existing library. Work around this by
    # loading through a uniquely-named symlink.
    #
    # For example, h5py and pyzmq both have a native submodule called utils.so. Without this
    # workaround, if you loaded them both, their __file__ attributes would appear different,
    # but the second one would actually have been loaded from the first one's file,
    def extract_so(self):
        filename = self.finder.extract_if_changed(self.finder.zip_path(self.path))
        linkname = join(dirname(filename), self.name + ".so")
        if linkname != filename:
            if exists(linkname):
                os.remove(linkname)
            os.symlink(filename, linkname)
        return linkname

    def load_needed(self, filename):
        with self.needed_lock, open(filename, "rb") as so_file:
            ef = ELFFile(so_file)
            dynamic = ef.get_section_by_name(".dynamic")
            if not dynamic:
                raise Exception(filename + " has no .dynamic section")

            for tag in dynamic.iter_tags():
                if tag.entry.d_tag != "DT_NEEDED":
                    continue
                soname = tag.needed
                if soname in self.needed_loaded:
                    continue

                try:
                    needed_filename = self.finder.extract_if_changed("chaquopy/lib/" + soname)
                except FileNotFoundError:
                    # Maybe it's a system library, or one of the libraries loaded by
                    # AndroidPlatform.loadNativeLibs. If the library is truly missing, we will
                    # get an exception in ctypes.CDLL or ExtensionFileLoader.create_module.
                    continue
                self.load_needed(needed_filename)

                # Before API 23, the only dlopen mode was RTLD_GLOBAL, and RTLD_LOCAL was
                # ignored. From API 23, RTLD_LOCAL is available and used by default, just like
                # in Linux (#5323). We use RTLD_GLOBAL, so that the library's symbols are
                # available to subsequently-loaded libraries.
                #
                # It doesn't look like the library is closed when the CDLL object is garbage
                # collected, but this isn't documented, so keep a reference for safety.
                self.needed_loaded[soname] = ctypes.CDLL(needed_filename, ctypes.RTLD_GLOBAL)


LOADERS = [
    (".py", SourceAssetLoader),
    (".so", ExtensionAssetLoader),
    # No current need for a SourcelessFileLoader, since we never include .pyc files in the
    # assets.
]


# Protects `extract` and `read` with locks, because they seek the underlying file object.
# `getinfo` and `infolist` are already thread-safe, because the ZIP index is completely read
# during construction. However, `open` cannot be made thread-safe without a lot of work, so it
# should not be used except via `extract` or `read`.
class ConcurrentZipFile(ZipFile):
    def __init__(self, *args, **kwargs):
        ZipFile.__init__(self, *args, **kwargs)
        self.lock = RLock()

        # ZIP files *may* have individual entries for directories, but we can't rely on it,
        # so we build an index to support `isdir` and `listdir`.
        self.dir_index = {"": set()}  # Provide empty listing for root even if ZIP is empty.
        for name in self.namelist():
            parts = name.rstrip("/").split("/")
            while parts:
                parent = "/".join(parts[:-1])
                if parent in self.dir_index:
                    self.dir_index[parent].add(parts[-1])
                    break
                else:
                    self.dir_index[parent] = set([parts.pop()])
        self.dir_index = {k: sorted(v) for k, v in self.dir_index.items()}

    def extract(self, member, target_dir):
        if not isinstance(member, ZipInfo):
            member = self.getinfo(member)
        with self.lock:
            # ZipFile.extract does not set any metadata (https://bugs.python.org/issue32170),
            # so set the timestamp manually. See makeZip in PythonPlugin.groovy for how these
            # timestamps are generated.
            out_filename = ZipFile.extract(self, member, target_dir)
            os.utime(out_filename, (time.time(), timegm(member.date_time)))
        return out_filename

    # The timestamp is the the last thing set by `extract`, so if the app gets killed in the
    # middle of an extraction, the timestamps won't match and we'll know we need to extract the
    # file again.
    #
    # However, since we're resetting all ZIP timestamps for a reproducible build, we can't rely
    # on them to tell us which files have changed after an app update. Instead,
    # initialize_importlib just removes the whole cache directory if its corresponding ZIP has
    # changed.
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
            self.extract(member, target_dir)
        return out_filename

    def read(self, member):
        with self.lock:
            return ZipFile.read(self, member)

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
