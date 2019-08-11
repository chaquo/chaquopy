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
from os.path import basename, dirname, exists, join
from pkgutil import get_importer
import re
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
from java.io import IOException


PATHNAME_PREFIX = "<chaquopy>/"


def initialize(context, build_json, app_path):
    initialize_importlib(context, build_json, app_path)
    initialize_imp()
    initialize_pkg_resources()


def initialize_importlib(context, build_json, app_path):
    # Remove nonexistent default paths (#5410)
    sys.path = [p for p in sys.path if exists(p)]

    global ASSET_PREFIX
    ASSET_PREFIX = join(context.getCacheDir().toString(), Common.ASSET_DIR, "AssetFinder")

    ep_json = build_json.get("extractPackages")
    extract_packages = set(ep_json.get(i) for i in range(ep_json.length()))
    sys.path_hooks.insert(0, partial(AssetFinder, context, extract_packages))
    asset_finders = []
    sp = context.getSharedPreferences(Common.ASSET_DIR, context.MODE_PRIVATE)
    assets_json = build_json.get("assets")

    # extract_package extracts both requirements ZIPs to the same cache directory, so if one
    # ZIP changes, both directories have to be removed.
    requirements_updated = False

    for i, asset_name in enumerate(app_path):
        entry = join(ASSET_PREFIX, asset_name)
        sys.path.insert(i, entry)
        finder = get_importer(entry)
        assert isinstance(finder, AssetFinder), ("Finder for '{}' is {}"
                                                 .format(entry, type(finder).__name__))
        asset_finders.append(finder)

        # See also similar code in AndroidPlatform.java.
        sp_key = "asset." + asset_name
        new_hash = assets_json.get(asset_name)
        is_requirements = asset_name.startswith("requirements")
        if (sp.getString(sp_key, "") != new_hash) or \
           (is_requirements and requirements_updated):
            if exists(finder.extract_root):
                rmtree(finder.extract_root)
            sp.edit().putString(sp_key, new_hash).apply()
            if is_requirements:
                requirements_updated = True

    # We do this here because .pth files may contain executable code which imports modules. If
    # we processed each zip's .pth files in AssetFinder.__init__, the finder itself wouldn't
    # be available to the system for imports yet.
    #
    # This is based on site.addpackage, which we can't use directly because we need to set the
    # local variable `sitedir` to accommodate the trick used by protobuf (see test_android).
    for finder in asset_finders:
        sitedir = finder.path  # noqa: F841 (see note above)
        for pth_filename in finder.zip_file.pth_files:
            pth_content = finder.zip_file.read(pth_filename).decode("UTF-8")
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
    # then that copy will take priority because the requirements ZIP is earlier on sys.path.
    import pkg_resources

    # Search for top-level .dist-info directories (see pip_install.py).
    def distribution_finder(finder, entry, only):
        dist_infos = [name for name in finder.zip_file.listdir("")
                      if name.endswith(".dist-info")]
        for dist_info in dist_infos:
            yield pkg_resources.Distribution.from_location(entry, dist_info)

    pkg_resources.register_finder(AssetFinder, distribution_finder)
    pkg_resources.working_set = pkg_resources.WorkingSet()

    class AssetProvider(pkg_resources.NullProvider):
        def __init__(self, module):
            super().__init__(module)
            self.zip_file = self.loader.finder.zip_file

        def _has(self, path):
            try:
                self.zip_file.getinfo(self.loader._zip_path(path))
                return True
            except KeyError:
                return self._isdir(path)

        def _isdir(self, path):
            return self.zip_file.isdir(self.loader._zip_path(path))

        def _listdir(self, path):
            return self.zip_file.listdir(self.loader._zip_path(path))

    pkg_resources.register_loader_type(AssetLoader, AssetProvider)


class AssetFinder:
    zip_file_lock = RLock()
    zip_file_cache = {}

    def __init__(self, context, extract_packages, path):
        try:
            self.context = context  # Also used in tests.
            self.extract_packages = extract_packages
            self.path = path

            self.extract_root = path
            self.prefix = ""
            while True:
                try:
                    # For non-asset paths, get_zip_file will raise InvalidAssetPathError, which
                    # we catch below.
                    self.zip_file = self.get_zip_file(self.extract_root)
                    break
                except IOException:
                    self.prefix = join(basename(self.extract_root), self.prefix)
                    self.extract_root = dirname(self.extract_root)
            os.makedirs(self.extract_root, exist_ok=True)

            self.package_path = [path]
            self.other_zips = []
            abis = [Common.ABI_COMMON, AndroidPlatform.ABI]
            abi_match = re.search(r"^(.*)-({})\.zip$".format("|".join(abis)),
                                  self.extract_root)
            if abi_match:
                for abi in abis:
                    abi_archive = "{}-{}.zip".format(abi_match.group(1), abi)
                    if abi_archive != self.extract_root:
                        self.package_path.append(join(abi_archive, self.prefix))
                        self.other_zips.append(self.get_zip_file(abi_archive))

        # If we raise ImportError, the finder is silently skipped. This is what we want only if
        # the path entry isn't an asset path: all other errors should abort the import,
        # including when the asset doesn't exist.
        except InvalidAssetPathError:
            raise ImportError(format_exc())
        except ImportError:
            raise Exception(format_exc())

    def __repr__(self):
        return "<AssetFinder({!r})>".format(self.path)

    def get_zip_file(self, path):
        match = re.search(r"^{}/(.+)$".format(ASSET_PREFIX), path)
        if not match:
            raise InvalidAssetPathError("not an asset path: '{}'".format(path))
        asset_path = join(Common.ASSET_DIR, match.group(1))  # Relative to assets root

        with self.zip_file_lock:
            zip_file = self.zip_file_cache.get(asset_path)
            if not zip_file:
                zip_file = ConcurrentZipFile(AssetFile(self.context, asset_path))
                self.zip_file_cache[asset_path] = zip_file
            return zip_file

    def find_spec(self, mod_name, target=None):
        spec = None
        loader = self.find_module(mod_name)
        if loader:
            spec = util.spec_from_loader(mod_name, loader)
            if loader.is_package(mod_name):
                spec.submodule_search_locations = self._get_path(mod_name)
        else:
            base_name = mod_name.rpartition(".")[2]
            if self.zip_file.isdir(join(self.prefix, base_name)):
                # Possible namespace package.
                spec = machinery.ModuleSpec(mod_name, None)
                spec.submodule_search_locations = self._get_path(mod_name)
        return spec

    def _get_path(self, mod_name):
        base_name = mod_name.rpartition(".")[2]
        return [join(entry, base_name) for entry in self.package_path]

    def find_module(self, mod_name):
        # It may seem weird to ignore all but the last word of mod_name, but that's what the
        # standard Python 3 finder does too.
        prefix = join(self.prefix, mod_name.rpartition(".")[2])
        # Packages take priority over modules (https://stackoverflow.com/questions/4092395/)
        for infix in ["/__init__", ""]:
            for suffix, loader_cls in LOADERS:
                try:
                    zip_info = self.zip_file.getinfo(prefix + infix + suffix)
                except KeyError:
                    continue
                if infix == "/__init__" and mod_name in self.extract_packages:
                    self.extract_package(prefix)
                return loader_cls(self, mod_name, zip_info)

        return None

    # Called by pkgutil.iter_modules.
    def iter_modules(self, prefix=""):
        # Finders may be created for nonexistent paths, e.g. if a package contains only
        # pure-Python code, then its directory won't exist in the ABI ZIP.
        if not self.zip_file.isdir(self.prefix):
            return

        for filename in self.zip_file.listdir(self.prefix):
            abs_filename = join(self.prefix, filename)
            if self.zip_file.isdir(abs_filename):
                for sub_filename in self.zip_file.listdir(abs_filename):
                    if getmodulename(sub_filename) == "__init__":
                        yield prefix + filename, True
                        break
            else:
                mod_base_name = getmodulename(filename)
                if mod_base_name and (mod_base_name != "__init__"):
                    yield prefix + mod_base_name, False

    # TODO: use dir_index via isdir and listdir??
    def extract_package(self, package_rel_dir):
        prefix = package_rel_dir.rstrip("/") + "/"
        for zf in [self.zip_file] + self.other_zips:
            for info in zf.infolist():
                filename = info.filename
                if filename.startswith(prefix) and not filename.endswith("/"):
                    self.extract_if_changed(info, zip_file=zf)

    def extract_if_changed(self, member, zip_file=None):
        if zip_file is None:
            zip_file = self.zip_file
        return zip_file.extract_if_changed(member, self.extract_root)


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
        if exists(path):
            with open(path, "rb") as f:
                return f.read()
        try:
            return self.finder.zip_file.read(self._zip_path(path))
        except KeyError as e:
            raise OSError(str(e))  # "There is no item named '{}' in the archive"

    def _zip_path(self, path):
        match = re.search(r"^{}/(.+)$".format(self.finder.extract_root), path)
        if not match:
            raise OSError("{} can't access '{}'".format(self.finder, path))
        return match.group(1)


# SourceFileLoader will access both the source and bytecode files via AssetLoader.get_data.
class SourceAssetLoader(AssetLoader, machinery.SourceFileLoader):
    def path_stats(self, path):
        return {"mtime": timegm(self.zip_info.date_time),
                "size": self.zip_info.file_size}


class ExtensionAssetLoader(AssetLoader, machinery.ExtensionFileLoader):
    def create_module(self, spec):
        out_filename = self.extract_so()
        load_needed(out_filename)
        return super().create_module(spec)

    # In API level 22 and older, when asked to load a library with the same basename as one
    # already loaded, the dynamic linker will return the existing library. Work around this by
    # loading through a uniquely-named symlink.
    def extract_so(self):
        filename = self.finder.extract_if_changed(self.zip_info)
        linkname = join(dirname(filename), self.name + ".so")
        if linkname != filename:
            if exists(linkname):
                os.remove(linkname)
            os.symlink(filename, linkname)
        return linkname


needed_lock = RLock()
needed_loaded = {}

# Before API level 18, the dynamic linker only searches for DT_NEEDED libraries in system
# directories, so we need to load them manually in dependency order (#5323).
#
# It's not an error if we don't find a library: maybe it's a system library, or one of the
# libraries loaded by AndroidPlatform.loadNativeLibs.
def load_needed(filename):
    with needed_lock, open(filename, "rb") as so_file:
        ef = ELFFile(so_file)
        dynamic = ef.get_section_by_name(".dynamic")
        if not dynamic:
            raise Exception(filename + " has no .dynamic section")

        for tag in dynamic.iter_tags():
            if tag.entry.d_tag != "DT_NEEDED":
                continue
            soname = tag.needed
            if soname in needed_loaded:
                continue

            for entry in sys.path:
                finder = get_importer(entry)
                if not isinstance(finder, AssetFinder):
                    continue
                try:
                    zip_info = finder.zip_file.getinfo("chaquopy/lib/" + soname)
                except KeyError:
                    continue
                needed_filename = finder.extract_if_changed(zip_info)
                load_needed(needed_filename)

                # Before API 23, the only dlopen mode was RTLD_GLOBAL, and RTLD_LOCAL was
                # ignored. From API 23, RTLD_LOCAL is available and used by default, just like
                # in Linux (#5323). We use RTLD_GLOBAL, so that the library's symbols are
                # available to subsequently-loaded libraries.
                #
                # It doesn't look like the library is closed when the CDLL object is garbage
                # collected, but this isn't documented, so keep a reference for safety.
                needed_loaded[soname] = ctypes.CDLL(needed_filename, ctypes.RTLD_GLOBAL)
                break


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
        self.pth_files = []
        for name in self.namelist():
            parts = name.rstrip("/").split("/")
            while parts:
                parent = "/".join(parts[:-1])
                if parent in self.dir_index:
                    self.dir_index[parent].add(parts[-1])
                    break
                else:
                    self.dir_index[parent] = set([parts.pop()])
            if ("/" not in name) and (name.endswith(".pth")):
                self.pth_files.append(name)

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

    def isdir(self, path):
        path = path.rstrip("/")
        return (path in self.dir_index)

    def listdir(self, path):
        path = path.rstrip("/")
        return sorted(self.dir_index[path])


class InvalidAssetPathError(ValueError):
    pass
