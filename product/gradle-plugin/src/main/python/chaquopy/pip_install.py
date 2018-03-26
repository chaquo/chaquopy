#!/usr/bin/env python

"""Copyright (c) 2018 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

import argparse
import email.parser
from glob import glob
from os.path import abspath, join
import re
import subprocess
import sys

from pip._vendor.distlib.database import InstalledDistribution
from pip.utils import rmtree


class PipInstall(object):

    def main(self):
        self.args = parse_args()
        self.abis_installed = []
        self.dist_info = {}
        try:
            abi = self.args.android_abis[0]
            native_reqs = self.pip_install(abi, self.args.reqs)
            if native_reqs:
                self.args.pip_options.append("--no-deps")
                for abi in self.args.android_abis[1:]:
                    self.pip_install(abi, native_reqs)
            else:
                log("No native packages found: skipping other ABIs")
        except CommandError as e:
            log(e, file=sys.stderr)
            sys.exit(1)

    def pip_install(self, abi, reqs):
        log("Installing for", abi)
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "--target", self.args.target,
                                   "--platform", self.platform_tag(abi)] +
                                  self.args.pip_options + reqs)
        except subprocess.CalledProcessError as e:
            raise CommandError("Exit status {}".format(e.returncode))

        native_reqs = []
        for dist_info_dir in self.dist_info_dirs():
            dist = InstalledDistribution(dist_info_dir)
            wheel_info = email.parser.Parser().parse(open(join(dist_info_dir, "WHEEL")))
            if wheel_info.get("Root-Is-Purelib", "false") == "false":
                native_reqs.append("{}=={}".format(dist.name, dist.version))

            mismatches = []
            for path, hash_str, size in dist.list_installed_files():
                path_abs = abspath(join(self.args.target, path))
                if not path_abs.startswith(self.args.target):
                    # pip's gone and installed something outside of the target directory.
                    raise CommandError("{}-{}: invalid path in RECORD: '{}'"
                                       .format(dist.name, dist.version, path))
                if path_abs.startswith(dist_info_dir):
                    continue

                new_info = "({}, {})".format(hash_str, size)  # Avoid u"" inconsistency in tests.
                existing_info = self.dist_info.setdefault(path, new_info)
                if existing_info != new_info:
                    # Show all mismatches at once, to save time when testing new packages.
                    mismatches.append(
                        "{}-{}: file '{}' from ABIs {!r} {} does not match copy from ABI '{}' {}"
                        .format(dist.name, dist.version, path, self.abis_installed,
                                existing_info, abi, new_info))

            if mismatches:
                raise CommandError("\n".join(mismatches))
            rmtree(dist_info_dir)  # Allow the next ABI to be installed over the top.

        self.abis_installed.append(abi)
        return native_reqs

    def dist_info_dirs(self):
        return glob(join(self.args.target, "*.dist-info"))

    def platform_tag(self, abi):
        return "android_15_" + re.sub(r"[-.]", "_", abi)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", metavar="DIR", type=abspath, required=True)
    ap.add_argument("--android-abis", metavar="ABI", nargs="+", required=True)

    # Passing the requirements this way ensures their order is maintained on the pip install
    # command line, which may be significant because of pip's simple-minded dependency
    # resolution (https://github.com/pypa/pip/issues/988).
    ap.set_defaults(reqs=[])
    ap.add_argument("--req", metavar="SPEC_OR_WHEEL", dest="reqs", action="append")
    ap.add_argument("--req-file", metavar="FILE", dest="reqs", action=ReqFileAppend)

    ap.add_argument("pip_options", nargs="*")
    return ap.parse_args()


class ReqFileAppend(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        getattr(namespace, self.dest).extend(["-r", value])


class CommandError(Exception):
    pass


def log(*args, **kwargs):
    print(*args, **kwargs)
    # Need to flush, otherwise output appears in the wrong order relative to pip output, when
    # passing through MSYS2 Python -> Gradle -> Android Studio.
    kwargs.get("file", sys.stdout).flush()


if __name__ == "__main__":
    PipInstall().main()
