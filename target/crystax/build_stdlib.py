import argparse
import os.path
import zipfile


IGNORE_DIR = (
    'site-packages',
    'curses',
    'dbm',
    'distutils',
    'idlelib',
    'lib2to3',
    'msilib',
    'pydoc_data',
    'tkinter',
    'turtledemo',
    'venv',
    'ensurepip',

# 2.7 specific
    'bsddb',
    'lib-tk'
)

IGNORE_FILE = (
   'site.py',
   'sysconfig.py',
   'doctest.py',
   'turtle.py',
   'tabnanny.py',
   'this.py',
   '__phello__.foo.py',
   '_osx_support.py',
   'asyncio/test_utils.py',

# 2.7 specific
   'anydbm.py',
   'user.py',
   'whichdb.py',
)


def dir_in_interest(arch_path):
    for exclusion in IGNORE_DIR:
        if arch_path == exclusion:
            return False
    return True


def file_in_interest(fs_path, arch_path):
    if arch_path in IGNORE_FILE:
        return False
    return True


def in_interest(fs_path, arch_path, is_dir, pathbits):
    name = pathbits[-1]
    if is_dir:
        if (name == '__pycache__' or name == 'test' or name == 'tests'):
            return False
        if arch_path.startswith('plat-'):
            return False
    else:
        if not arch_path.endswith('.py'):
            return False
    if is_dir:
        return dir_in_interest(arch_path)
    else:
        return file_in_interest(fs_path, arch_path)


def enum_content(seed, catalog, pathbits = None):
    if pathbits is None:
        fs_path = seed
        is_dir = True
    else:
        fs_path = os.path.join(seed, *pathbits)
        is_dir = os.path.isdir(fs_path)
    if pathbits is not None:
        arc_path = '/'.join(pathbits)
        if not in_interest(fs_path, arc_path, is_dir, pathbits):
            return
        if not is_dir:
            catalog.append((fs_path, arc_path))
    else:
        pathbits = []
    if is_dir:
        files = []
        dirs = []
        for name in os.listdir(fs_path):
            p = os.path.join(fs_path, name)
            if os.path.isdir(p):
                dirs.append(name)
            else:
                files.append(name)
        for name in sorted(dirs):
            pathbits.append(name)
            enum_content(seed, catalog, pathbits)
            del pathbits[-1]
        for name in sorted(files):
            pathbits.append(name)
            enum_content(seed, catalog, pathbits)
            del pathbits[-1]


def build_stdlib():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pysrc-root', required=True)
    parser.add_argument('--output-zip', required=True)
    parser.add_argument('--py2', action='store_true')
    args = parser.parse_args()

    dirhere = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
    stdlib_srcdir = os.path.normpath(os.path.abspath(os.path.join(args.pysrc_root, 'Lib')))
    zipfilename = os.path.normpath(os.path.abspath(args.output_zip))
    display_zipname = os.path.basename(zipfilename)

    catalog = []
    enum_content(stdlib_srcdir, catalog)
    catalog += [
        (os.path.join(dirhere, 'site.py'), 'site.py'),
        (os.path.join(dirhere, 'sysconfig.py'), 'sysconfig.py'),
        (os.path.join(dirhere, '_sysconfigdata.py'), '_sysconfigdata.py'),
    ]
    if args.py2:
        catalog += [(os.path.join(dirhere, '_sitebuiltins.py'), '_sitebuiltins.py')]

    print("::: compiling python-stdlib zip package '{0}' ...".format(zipfilename))
    with zipfile.ZipFile(zipfilename, "w", zipfile.ZIP_DEFLATED) as fzip:
        for entry in catalog:
            fname, arcname = entry[0], entry[1]
            fzip.write(fname, arcname)
            print("::: {0} >>> {1}/{2}".format(fname, display_zipname, arcname))


if __name__ == '__main__':
    build_stdlib()
