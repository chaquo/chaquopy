"""Copyright (c) 2017 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

from calendar import timegm
import ctypes
from functools import partial
import imp
import io
import marshal
import os.path
from os.path import basename, dirname, exists, join
import pkgutil
import re
import shutil
import struct
import sys
import time
from threading import RLock
from traceback import format_exc
from types import ModuleType
from zipfile import ZipFile, ZipInfo

from java._vendor.elftools.elf.elffile import ELFFile
from java._vendor import six

from android.content.res import AssetManager
from com.chaquo.python import Common
from com.chaquo.python.android import AndroidPlatform
from java import jarray, jbyte
from java.io import IOException
from java.lang import Integer

if six.PY3:
    from tokenize import detect_encoding


ASSET_PREFIX = "/android_asset"
PATHNAME_PREFIX = "<chaquopy>/"


def initialize(context, build_json, app_path):
    ep_json = build_json.get("extractPackages")
    extract_packages = set(ep_json.get(i) for i in range(ep_json.length()))

    # In both Python 2 and 3, the standard implementations of imp.{find,load}_module do not use
    # the PEP 302 import system. They are therefore only capable of loading from directory
    # trees and built-in modules, and will ignore both our path_hook and the standard one for
    # zipimport. To accommodate code which uses these functions, we provide these replacements.
    global find_module_original, load_module_original
    find_module_original = imp.find_module
    load_module_original = imp.load_module
    imp.find_module = find_module_override
    imp.load_module = load_module_override

    sys.path_hooks.insert(0, partial(AssetFinder, context, extract_packages))
    asset_finders = []
    for i, asset_name in enumerate(app_path):
        entry = str(join(ASSET_PREFIX, Common.ASSET_DIR, asset_name))
        sys.path.insert(i, entry)
        finder = pkgutil.get_importer(entry)
        assert isinstance(finder, AssetFinder), ("Finder for '{}' is {}"
                                                 .format(entry, type(finder).__name__))
        asset_finders.append(finder)

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


# Unlike the other APIs in this file, find_module does not take names containing dots.
def find_module_override(base_name, path=None):
    try:
        return find_module_original(base_name, path)
    except Exception:
        pass

    if path is None:
        path = sys.path
    for entry in path:
        finder = pkgutil.get_importer(entry)
        if finder is not None and hasattr(finder, "prefix"):
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

                # The documentation says the returned pathname should be the empty string when
                # a module isn't a package and "does not live in a file". However, neither
                # Python 2 or 3 actually do this for built-in modules (see test_android).
                # Anyway, the only thing the user can do with this value is pass it to
                # load_module, so we should be safe to set it to any string we want.
                pathname = PATHNAME_PREFIX + join(entry, base_name)
                return (None, pathname, ("", "", mod_type))

    raise ImportError("No module named '{}' found in {}".format(base_name, path))


def load_module_override(load_name, file, pathname, description):
    # In Python 2, load_module_original will return an empty module when asked to load a
    # directory that doesn't exist. It may have other undesirable behaviour as well, so avoid
    # calling it unless our parameters came from find_module_original.
    if (pathname is None) or (not pathname.startswith(PATHNAME_PREFIX)):
        return load_module_original(load_name, file, pathname, description)
    else:
        entry, base_name = os.path.split(pathname[len(PATHNAME_PREFIX):])
        finder = pkgutil.get_importer(entry)
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
                zip_file = ConcurrentZipFile(AssetFile(self.context.getAssets(), path))
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
            if self.zip_file.has_dir(join(self.prefix, base_name)):
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
        package_dir = join(self.extract_root, package_rel_dir)
        if exists(package_dir):
            shutil.rmtree(package_dir)  # Just do it the easy way for now.
        for zf in [self.zip_file] + self.other_zips:
            for info in zf.infolist():
                if info.filename.startswith(package_rel_dir):
                    zf.extract(info, self.extract_root)


class AssetLoader(object):
    def __init__(self, finder, real_name, zip_info):
        self.finder = finder
        self.mod_name = self.real_name = real_name
        self.zip_info = zip_info

    def __repr__(self):
        return ("<{}.{}({}, {!r})>"  # Distinguish from standard loaders with the same names.
                .format(__name__, type(self).__name__, self.finder, self.real_name))

    def load_module(self, real_name, load_name=None):
        assert real_name == self.real_name
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
        match = re.search(r"^{}/(.+)$".format(self.finder.archive), path)
        if not match:
            raise IOError("{} can't access '{}'".format(self.finder, path))
        try:
            return self.finder.zip_file.read(match.group(1))
        except KeyError as e:
            raise IOError(str(e))  # "There is no item named '{}' in the archive"

    def is_package(self, mod_name):
        return basename(self.get_filename(mod_name)).startswith("__init__.")

    def get_code(self, mod_name):
        return None  # Not implemented, but required for importlib.abc.InspectLoader.

    # Overridden in SourceFileLoader
    def get_source(self, mod_name):
        return None

    def get_filename(self, mod_name):
        assert mod_name == self.mod_name
        for ep in self.finder.extract_packages:
            if mod_name.startswith(ep):
                root = self.finder.extract_root
                break
        else:
            root = self.finder.archive
        return join(root, self.zip_info.filename)


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
    needed_lock = RLock()
    needed = {}

    def load_module_impl(self):
        out_filename = self.extract_if_changed(self.zip_info)
        with self.needed_lock:
            self.load_needed(out_filename)
        # imp.load_{source,compiled,dynamic} are undocumented in Python 3, but still present.
        mod = imp.load_dynamic(self.mod_name, out_filename)
        sys.modules[self.mod_name] = mod
        self.set_mod_attrs(mod)

    # Before API level 18, the dynamic linker only searches for DT_NEEDED libraries in system
    # directories, so we need to load them manually in dependency order (#5323).
    def load_needed(self, filename):
        with open(filename, "rb") as so_file:
            ef = ELFFile(so_file)
            dynamic = ef.get_section_by_name(".dynamic")
            if not dynamic:
                return

            for tag in dynamic.iter_tags():
                if tag.entry.d_tag == "DT_NEEDED":
                    soname = tag.needed
                    if soname in self.needed:
                        continue

                    try:
                        # We don't need to worry about other_zips because all native modules
                        # and libraries for a given ABI will always end up in the same ZIP.
                        zip_info = self.finder.zip_file.getinfo("chaquopy/lib/" + soname)
                    except KeyError:
                        # Maybe it's a system library, or one of the libraries loaded by
                        # AndroidPlatform.loadNativeLibs.
                        continue
                    needed_filename = self.extract_if_changed(zip_info)
                    self.load_needed(needed_filename)

                    # Before API 23, the only dlopen mode was RTLD_GLOBAL, and RTLD_LOCAL was
                    # ignored. From API 23, RTLD_LOCAL is available and the default, just like
                    # in Linux (#5323). We use RTLD_GLOBAL, so that the library's symbols are
                    # available to subsequently-loaded libraries.
                    dll = ctypes.CDLL(needed_filename, ctypes.RTLD_GLOBAL)

                    # The library isn't currently closed when the CDLL object is garbage
                    # collected, but this isn't documented, so keep a reference for safety.
                    self.needed[soname] = dll

    def extract_if_changed(self, zip_info):
        out_filename = join(self.finder.extract_root, zip_info.filename)
        if exists(out_filename):
            existing_stat = os.stat(out_filename)
            need_extract = (existing_stat.st_size != zip_info.file_size or
                            existing_stat.st_mtime != timegm(zip_info.date_time))
        else:
            need_extract = True

        if need_extract:
            self.finder.zip_file.extract(zip_info, self.finder.extract_root)
        return out_filename


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

        self.dir_set = set()
        self.pth_files = []
        for name in self.namelist():
            dir_name, base_name = os.path.split(name)
            if dir_name:
                self.dir_set.add(dir_name)
            if (not dir_name) and base_name.endswith(".pth"):
                self.pth_files.append(base_name)

    def extract(self, member, target_dir):
        if not isinstance(member, ZipInfo):
            member = self.getinfo(member)
        with self.lock:
            # ZipFile.extract does not set any metadata (https://bugs.python.org/issue32170).
            out_filename = ZipFile.extract(self, member, target_dir)
            os.utime(out_filename, (time.time(), timegm(member.date_time)))
        return out_filename

    def read(self, member):
        with self.lock:
            return ZipFile.read(self, member)

    # ZIP files *may* have individual entries for directories, but we shouldn't rely on it, so
    # we build a directory set in __init__.
    def has_dir(self, dir_name):
        return (dir_name in self.dir_set)

class AssetFile(object):
    # Raises InvalidAssetPathError if the path is not an asset path, or IOException if the
    # asset does not exist.
    def __init__(self, asset_manager, path):
        match = re.search(r"^{}/(.+)$".format(ASSET_PREFIX), path)
        if not match:
            raise InvalidAssetPathError("not an {} path: '{}'".format(ASSET_PREFIX, path))
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
