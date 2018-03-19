#!/usr/bin/env python

"""Copyright (c) 2017 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

import argparse
import csv
import email.parser
import os
from os.path import dirname, exists, join, normpath
import re
import shutil
import subprocess
import sys

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
                for abi in self.args.android_abis[1:]:
                    self.pip_install(abi, native_reqs)
            else:
                print("Found no native packages")  # Explains why only one ABI appears in log.
        except subprocess.CalledProcessError as e:
            print("Exit status {}".format(e.returncode), file=sys.stderr)
            sys.exit(1)
        except CommandError as e:
            print("Chaquopy: {}".format(e), file=sys.stderr)
            sys.exit(1)

    def pip_install(self, abi, reqs):
        print("Installing for", abi)
        sys.stdout.flush()  # "print() output was appearing after pip output on MSYS2.
        abi_dir = "{}.{}".format(self.args.target, abi)
        if exists(abi_dir):
            rmtree(abi_dir)
        os.makedirs(abi_dir)
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "--target", abi_dir,
                               "--platform", self.platform_tag(abi)] +
                              self.args.pip_options + reqs)
        native_reqs = self.merge_dir(abi, abi_dir)
        rmtree(abi_dir)
        self.abis_installed.append(abi)
        return native_reqs

    def merge_dir(self, abi, abi_dir):
        native_reqs = []
        for filename in os.listdir(abi_dir):
            match = re.search(r"^(.+)-(.+)\.dist-info$", filename)
            if not match:
                continue
            dist_info_dir = join(abi_dir, filename)
            pkg_name, pkg_ver = match.group(1, 2)

            wheel_info = email.parser.Parser().parse(open(join(dist_info_dir, "WHEEL")))
            is_pure_str = wheel_info.get("Root-Is-Purelib", "false")
            if is_pure_str != "true":
                native_reqs.append("{}=={}".format(pkg_name, pkg_ver))

            mismatches = []
            for path, hash_str, size in csv.reader(open(join(dist_info_dir, "RECORD"))):
                if not normpath(join(abi_dir, path)).startswith(normpath(abi_dir)):
                    # pip's gone and installed something outside of abi_dir.
                    raise CommandError("invalid path in RECORD for {}-{}: {}"
                                       .format(pkg_name, pkg_ver, path))
                if path.startswith(filename):  # i.e. it's in the .dist-info directory
                    continue
                new_info = (hash_str, size)
                existing_info = self.dist_info.get(path)
                if existing_info:
                    if existing_info != new_info:
                        mismatches.append(
                            "file '{}' from ABIs {!r} {} does not match copy from '{}' {}"
                            .format(path, self.abis_installed, existing_info, abi, new_info))
                else:
                    target_dir = dirname(join(self.args.target, path))
                    if not exists(target_dir):
                        os.makedirs(target_dir)
                    shutil.copy(join(abi_dir, path), target_dir)
                    self.dist_info[path] = new_info

            if mismatches:
                raise CommandError("\n".join(mismatches))

        return native_reqs

    def platform_tag(self, abi):
        return "android_15_" + re.sub(r"[-.]", "_", abi)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", metavar="DIR", required=True)
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


if __name__ == "__main__":
    PipInstall().main()
