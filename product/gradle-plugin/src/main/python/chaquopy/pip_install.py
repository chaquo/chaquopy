#!/usr/bin/env python

"""Copyright (c) 2018 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

import argparse
import email.parser
from glob import glob
import logging
import os
from os.path import abspath, dirname, exists, join
import re
import subprocess
import sys

from pip._vendor.distlib.database import InstalledDistribution
from pip.utils import rmtree
import six


logger = logging.getLogger(__name__)

class PipInstall(object):

    def main(self):
        # This matches pip's own logging setup in pip/basecommand.py.
        self.parse_args()
        verbose = ("-v" in self.pip_options) or ("--verbose" in self.pip_options)
        logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                            stream=sys.stdout,
                            format=("%(asctime)s Chaquopy: %(message)s" if verbose
                                    else "Chaquopy: %(message)s"),
                            datefmt="%H:%M:%S")

        os.mkdir(join(self.target, "common"))
        self.installed_files = {}
        try:
            native_reqs = self.pip_install(self.android_abis[0], self.reqs)
            self.pip_options.append("--no-deps")
            for abi in self.android_abis[1:]:
                self.pip_install(abi, native_reqs)
            self.merge_common()
            logger.debug("Finished")
        except CommandError as e:
            logger.error(str(e))
            sys.exit(1)

    def pip_install(self, abi, reqs):
        logger.info("Installing for " + abi)
        abi_dir = join(self.target, abi)
        os.mkdir(abi_dir)
        if not reqs:
            return

        try:
            # Warning: `pip install --target` is very simple-minded: see
            # https://github.com/pypa/pip/issues/4625#issuecomment-375977073. Also, we've
            # altered its behaviour (in pip/commands/install.py) so it now just merges any
            # existing directories, and silently overwrites any existing files.
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "--target", abi_dir,
                                   "--platform", self.platform_tag(abi)] +
                                  self.pip_options + reqs)
        except subprocess.CalledProcessError as e:
            raise CommandError("Exit status {}".format(e.returncode))

        logger.debug("Checking install")
        native_reqs = []
        self.installed_files[abi] = {}
        for dist_info_dir in glob(join(abi_dir, "*.dist-info")):
            dist = InstalledDistribution(dist_info_dir)
            wheel_info = email.parser.Parser().parse(open(join(dist_info_dir, "WHEEL")))
            is_pure = (wheel_info.get("Root-Is-Purelib", "false") == "true")
            if not is_pure:
                native_reqs.append("{}=={}".format(dist.name, dist.version))

            for path, hash_str, size in dist.list_installed_files():
                path_abs = abspath(join(abi_dir, path))
                if not path_abs.startswith(abi_dir):
                    # pip's gone and installed something outside of the target directory.
                    raise CommandError("{}-{}: invalid path in RECORD: '{}'"
                                       .format(dist.name, dist.version, path))
                if path_abs.startswith(dist_info_dir):
                    continue
                if is_pure:
                    self.move_to_common(abi, path)
                else:
                    self.installed_files[abi][path] = (hash_str, size)

            rmtree(dist_info_dir)  # It may no longer reflect reality.

        return native_reqs

    def merge_common(self):
        logger.debug("Merging ABIs")
        for filename, info in six.iteritems(self.installed_files[self.android_abis[0]]):
            if all(self.installed_files[abi].get(filename) == info
                   for abi in self.android_abis[1:]):
                self.move_to_common(self.android_abis[0], filename)
                for abi in self.android_abis[1:]:
                    abi_filename = join(self.target, abi, filename)
                    os.remove(abi_filename)
                    try:
                        os.removedirs(dirname(abi_filename))
                    except OSError:
                        pass  # Directory is not empty.

        # If an ABI directory ended up empty, removedirs will have deleted it.
        for abi in self.android_abis:
            abi_dir = join(self.target, abi)
            if not exists(abi_dir):
                os.mkdir(abi_dir)

    def move_to_common(self, abi, filename):
        os.renames(join(self.target, abi, filename), join(self.target, "common", filename))

    def platform_tag(self, abi):
        return "android_15_" + re.sub(r"[-.]", "_", abi)

    def parse_args(self):
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
        ap.parse_args(namespace=self)


class ReqFileAppend(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        getattr(namespace, self.dest).extend(["-r", value])


class CommandError(Exception):
    pass


if __name__ == "__main__":
    PipInstall().main()
