"""Copyright (c) 2017 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

from calendar import timegm
import ctypes
from functools import partial
import imp
import io
import marshal
import os.path
from os.path import basename, dirname, exists, join, relpath
from pkgutil import get_importer
import re
from shutil import rmtree
import struct
import sys
import time
from threading import RLock
from traceback import format_exc
from types import ModuleType
from zipfile import ZipFile, ZipInfo

from java._vendor.elftools.elf.elffile import ELFFile
from java._vendor import six
from java.chaquopy import ASSET_PREFIX, AssetFile, InvalidAssetPathError

from android.os import Build
from com.chaquo.python import Common
from com.chaquo.python.android import AndroidPlatform
from java.io import IOException

if six.PY3:
    from tokenize import detect_encoding


PATHNAME_PREFIX = "<chaquopy>/"


def initialize(context, build_json, app_path):
    initialize_importlib(context, build_json, app_path)
    initialize_imp()
    initialize_pkg_resources()


def initialize_importlib(context, build_json, app_path):
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
        entry = str(join(ASSET_PREFIX, Common.ASSET_DIR, asset_name))
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
    # In both Python 2 and 3, the standard implementations of imp.{find,load}_module do not use
    # the PEP 302 import system. They are therefore only capable of loading from directory
    # trees and built-in modules, and will ignore both our path_hook and the standard one for
    # zipimport. To accommodate code which uses these functions, we provide these replacements.
    global find_module_original, load_module_original
    find_module_original = imp.find_module
    load_module_original = imp.load_module
    imp.find_module = find_module_override
    imp.load_module = load_module_override


# Unlike the other APIs in this file, find_module does not take names containing dots.
def find_module_override(base_name, path=None):
    try:
        return find_module_original(base_name, path)
    except Exception:
        pass

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
                    mod_type = imp.PKG_DIRECTORY
                else:
                    filename = loader.get_filename(real_name)
                    for suffix, mode, mod_type in imp.get_suffixes():
                        if filename.endswith(suffix):
                            break
                    else:
                        raise ValueError("Couldn't determine type of module '{}' from '{}'"
                                         .format(real_name, filename))

                # The documentation says that if the module "does not live in a file", the
                # returned tuple contains file=None and pathname="". However, the the only
                # thing the user is likely to do with these values is pass them to load_module,
                # so we should be safe to use them however we want.
                #
                # * file=None causes problems for SWIG-generated code such as
                #   tensorflow.python.pywrap_tensorflow_internal, so we return a dummy file-like
                #   object instead.
                # * `pathname` is used to communicate the location of the module to load_module
                #   below.
                return (six.BytesIO(),
                        PATHNAME_PREFIX + join(entry, base_name),
                        ("", "", mod_type))

    raise ImportError("No module named '{}' found in {}".format(base_name, path))


def load_module_override(load_name, file, pathname, description):
    # In Python 2, load_module_original will return an empty module when asked to load a
    # directory that doesn't exist. It may have other undesirable behaviour as well, so avoid
    # calling it unless our parameters came from find_module_original.
    if (pathname is None) or (not pathname.startswith(PATHNAME_PREFIX)):
        return load_module_original(load_name, file, pathname, description)
    else:
        entry, base_name = os.path.split(pathname[len(PATHNAME_PREFIX):])
        finder = get_importer(entry)
        real_name = join(finder.prefix, base_name).replace("/", ".")
        loader = finder.find_module(real_name)
        if real_name == load_name:
            return loader.load_module(real_name)
        else:
            if not isinstance(loader, AssetLoader):
                raise ImportError(
                    "{} does not support loading module '{}' under a different name '{}'"
                    .format(type(loader).__name__, real_name, load_name))
            return loader.load_module(real_name, load_name=load_name)


def initialize_pkg_resources():
    try:
        import pkg_resources
    except ImportError:
        return

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

        def get_resource_filename(self, manager, resource_name):
            # This would require extracting the resource to a temporary file, as in
            # pkg_resources.ZipProvider.
            raise NotImplementedError()

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


# Not inheriting any base class: they aren't available in Python 2.
class AssetFinder(object):
    zip_file_lock = RLock()
    zip_file_cache = {}

    def __init__(self, context, extract_packages, path):
        try:
            self.context = context  # Also used in tests.
            self.extract_packages = extract_packages
            self.path = path

            self.archive = path  # These two attributes have the same meaning as in zipimport.
            self.prefix = ""     #
            while True:  # Will be terminated by InvalidAssetPathError.
                try:
                    self.zip_file = self.get_zip_file(self.archive)
                    break
                except IOException:
                    self.prefix = join(basename(self.archive), self.prefix)
                    self.archive = dirname(self.archive)

            self.package_path = [path]
            self.other_zips = []
            abis = [Common.ABI_COMMON, AndroidPlatform.ABI]
            abi_match = re.search(r"^(.*)-({})\.zip$".format("|".join(abis)),
                                  self.archive)
            if abi_match:
                for abi in abis:
                    abi_archive = "{}-{}.zip".format(abi_match.group(1), abi)
                    if abi_archive != self.archive:
                        self.package_path.append(join(abi_archive, self.prefix))
                        self.other_zips.append(self.get_zip_file(abi_archive))

            self.extract_root = join(context.getCacheDir().toString(), Common.ASSET_DIR,
                                     "AssetFinder", basename(self.archive))

        # If we raise ImportError, the finder is silently skipped. This is what we want only if
        # the path entry isn't an /android_asset path: all other errors should abort the import,
        # including when the asset doesn't exist.
        except InvalidAssetPathError:
            raise ImportError(format_exc())
        except ImportError:
            raise Exception(format_exc())

    def __repr__(self):
        return "<AssetFinder({!r})>".format(self.path)

    def get_zip_file(self, path):
        with self.zip_file_lock:
            zip_file = self.zip_file_cache.get(path)
            if not zip_file:
                zip_file = ConcurrentZipFile(AssetFile(self.context, path))
                self.zip_file_cache[path] = zip_file
            return zip_file

    # This method will be called by Python 3.
    def find_loader(self, mod_name):
        loader = self.find_module(mod_name)
        path = []
        if loader:
            if loader.is_package(mod_name):
                path = self._get_path(mod_name)
        else:
            base_name = mod_name.rpartition(".")[2]
            if self.zip_file.isdir(join(self.prefix, base_name)):
                path = self._get_path(mod_name)
        return (loader, path)

    def _get_path(self, mod_name):
        base_name = mod_name.rpartition(".")[2]
        return [join(entry, base_name) for entry in self.package_path]

    # This method will be called by Python 2.
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

    def extract_package(self, package_rel_dir):
        filenames_in_zip = set()
        for zf in [self.zip_file] + self.other_zips:
            for info in zf.infolist():
                if info.filename.startswith(package_rel_dir) and \
                   not info.filename.endswith("/"):
                    filenames_in_zip.add(info.filename)
                    self.extract_if_changed(info, zip_file=zf)

        # Remove any leftover extracted files from previous versions of the app.
        for dirpath, _, filenames in os.walk(join(self.extract_root, package_rel_dir)):
            rel_dirpath = relpath(dirpath, self.extract_root)
            for name in filenames:
                if not name.endswith(".pyc") and \
                   join(rel_dirpath, name) not in filenames_in_zip:
                    os.remove(join(dirpath, name))

    def extract_if_changed(self, member, zip_file=None):
        if zip_file is None:
            zip_file = self.zip_file
        return zip_file.extract_if_changed(member, self.extract_root)


# Not inheriting any base class: they aren't available in Python 2.
class AssetLoader(object):
    def __init__(self, finder, real_name, zip_info):
        self.finder = finder
        self.mod_name = self.real_name = real_name
        self.zip_info = zip_info

    def __repr__(self):
        return ("<{}.{}({}, {!r})>"  # Distinguish from standard loaders with the same names.
                .format(__name__, type(self).__name__, self.finder, self.real_name))

    def load_module(self, real_name, load_name=None):
        self._check_name(real_name, self.real_name)
        self.mod_name = load_name or real_name
        is_reload = self.mod_name in sys.modules
        try:
            self.load_module_impl()
            # The module that ends up in sys.modules is not necessarily the one we just created
            # (e.g. see bottom of pygments/formatters/__init__.py).
            return sys.modules[self.mod_name]
        except Exception:
            if not is_reload:
                sys.modules.pop(self.mod_name, None)  # Don't leave a part-initialized module.
            raise

    def set_mod_attrs(self, mod):
        mod.__name__ = self.mod_name  # Native module creation may set this to the unqualified name.
        mod.__file__ = self.get_filename(self.mod_name)
        if self.is_package(self.mod_name):
            mod.__package__ = self.mod_name
            mod.__path__ = self.finder._get_path(self.real_name)
        else:
            mod.__package__ = self.mod_name.rpartition('.')[0]
        mod.__loader__ = self
        if sys.version_info[0] >= 3:
            # The import system sets __spec__ when using the import statement, but not when
            # load_module is called directly.
            import importlib.util
            mod.__spec__ = importlib.util.spec_from_loader(self.mod_name, self)

    # IOError became an alias for OSError in Python 3.4, and the get_data specification was
    # changed accordingly.
    def get_data(self, path):
        if exists(path):  # extractPackages is in effect.
            with open(path, "rb") as f:
                return f.read()
        try:
            return self.finder.zip_file.read(self._zip_path(path))
        except KeyError as e:
            raise IOError(str(e))  # "There is no item named '{}' in the archive"

    def _zip_path(self, path):
        match = re.search(r"^{}/(.+)$".format(self.finder.archive), path)
        if not match:
            raise IOError("{} can't access '{}'".format(self.finder, path))
        return match.group(1)

    def is_package(self, mod_name):
        return basename(self.get_filename(mod_name)).startswith("__init__.")

    # Overridden in SourceFileLoader
    def get_code(self, mod_name):
        return None

    # Overridden in SourceFileLoader
    def get_source(self, mod_name):
        return None

    def get_filename(self, mod_name):
        self._check_name(mod_name)
        for ep in self.finder.extract_packages:
            if (mod_name == ep) or mod_name.startswith(ep + "."):
                root = self.finder.extract_root
                break
        else:
            root = self.finder.archive
        return join(root, self.zip_info.filename)

    # Most loader methods will only work for the loader's own module. However, always allow the
    # name "__main__", which might be used by the runpy module.
    def _check_name(self, actual_name, expected_name=None):
        if expected_name is None:
            expected_name = self.mod_name
        if actual_name not in [expected_name, "__main__"]:
            raise AssertionError("actual={!r}, expected={!r}"
                                 .format(actual_name, expected_name))


# Irrespective of the Python version, we use the Python 3.6 .pyc layout (with size field).
PYC_HEADER_FORMAT = "<4siI"

class SourceFileLoader(AssetLoader):
    def load_module_impl(self):
        mod = sys.modules.get(self.mod_name)
        if mod is None:
            mod = ModuleType(self.mod_name)
            self.set_mod_attrs(mod)
            sys.modules[self.mod_name] = mod
        six.exec_(self.get_code(self.mod_name), mod.__dict__)

    def get_code(self, mod_name):
        self._check_name(mod_name)
        pyc_filename = join(self.finder.extract_root, self.zip_info.filename + "c")
        code = self.read_pyc(pyc_filename)
        if not code:
            # compile() doesn't impose the same restrictions as get_source().
            code = compile(self.get_source_bytes(), self.get_filename(self.mod_name), "exec",
                           dont_inherit=True)
            self.write_pyc(pyc_filename, code)
        return code

    # Should return a bytes string in Python 2, or a unicode string in Python 3, in both cases
    # with newlines normalized to "\n".
    def get_source(self, mod_name):
        self._check_name(mod_name)
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
        try:
            os.makedirs(pyc_dirname)
        except OSError:
            assert exists(pyc_dirname)
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
        # Older versions can't load two .so files with the same basename (#5478). Symlink
        # workaround was removed on this branch because of apparent filesystem corruption on
        # ***REMOVED*** devices (#5530).
        assert Build.VERSION.SDK_INT >= 23

        out_filename = self.finder.extract_if_changed(self.zip_info)
        load_needed(out_filename)
        # imp.load_{source,compiled,dynamic} are undocumented in Python 3, but still present.
        mod = imp.load_dynamic(self.mod_name, out_filename)
        sys.modules[self.mod_name] = mod
        self.set_mod_attrs(mod)


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


# These class names are based on the standard Python 3 loaders from importlib.machinery, though
# their interfaces are somewhat different.
LOADERS = [
    (".py", SourceFileLoader),
    (".so", ExtensionFileLoader),
    # No current need for a SourcelessFileLoader, since we exclude .pyc files from app.zip and
    # requirements.zip. To support this fully for both Python 2 and 3 would be non-trivial due
    # to the variation in bytecode file names and locations. However, we could select one
    # variation and use it for all Python versions.
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
        self.dir_index = {"": []}  # Provide empty listing for root even if ZIP is empty.
        self.pth_files = []
        for name in self.namelist():
            parts = name.rstrip("/").split("/")
            while parts:
                parent = "/".join(parts[:-1])
                if parent in self.dir_index:
                    self.dir_index[parent].append(parts[-1])
                    break
                else:
                    self.dir_index[parent] = [parts.pop()]
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
        return (path in self.dir_index)

    def listdir(self, path):
        return self.dir_index[path]
