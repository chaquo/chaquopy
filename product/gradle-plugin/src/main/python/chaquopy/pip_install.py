#!/usr/bin/env python

"""Copyright (c) 2018 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

import argparse
from copy import deepcopy
import email.parser
from glob import glob
import logging
import os
from os.path import abspath, dirname, exists, isdir, join
import re
import subprocess
import sys

from pip._internal.utils.misc import rmtree
from pip._vendor.distlib.database import InstalledDistribution
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
        abi_trees = {}
        try:
            abi = self.android_abis[0]
            pure_reqs, native_reqs, abi_trees[abi] = self.pip_install(abi, self.reqs)
            self.move_pure(pure_reqs, abi, abi_trees[abi])
            self.pip_options.append("--no-deps")
            for abi in self.android_abis[1:]:
                _, _, abi_trees[abi] = self.pip_install(abi, list(native_reqs))
            self.merge_common(abi_trees)
            logger.debug("Finished")
        except CommandError as e:
            logger.error(str(e))
            sys.exit(1)

    def pip_install(self, abi, reqs):
        logger.info("Installing for " + abi)
        abi_dir = join(self.target, abi)
        os.mkdir(abi_dir)
        if not reqs:
            return {}, {}, {}

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

        logger.debug("Reading dist-info")
        pure_reqs = {}
        native_reqs = {}
        abi_tree = {}
        for dist_info_dir in glob(join(abi_dir, "*.dist-info")):
            dist = InstalledDistribution(dist_info_dir)
            req_tree = {}
            for path, hash_str, size in dist.list_installed_files():
                path_abs = abspath(join(abi_dir, path))
                if not path_abs.startswith(abi_dir):
                    # pip's gone and installed something outside of the target directory.
                    raise CommandError("{}-{}: invalid path in RECORD: '{}'"
                                       .format(dist.name, dist.version, path))
                if not path_abs.startswith(dist_info_dir):
                    tree_add_path(req_tree, path, (hash_str, size))
            tree_merge_from(abi_tree, req_tree)

            wheel_info = email.parser.Parser().parse(open(join(dist_info_dir, "WHEEL")))
            is_pure = (wheel_info.get("Root-Is-Purelib", "false") == "true")
            req_spec = "{}=={}".format(dist.name, dist.version)
            (pure_reqs if is_pure else native_reqs)[req_spec] = req_tree

            rmtree(dist_info_dir)

        return pure_reqs, native_reqs, abi_tree

    def move_pure(self, pure_reqs, abi, abi_tree):
        logger.debug("Moving pure requirements")
        for req_tree in six.itervalues(pure_reqs):
            for path in common_paths(abi_tree, req_tree):
                self.move_to_common(abi, path)
                tree_remove_path(abi_tree, path)

    def merge_common(self, abi_trees):
        logger.debug("Merging ABIs")
        for path in common_paths(*abi_trees.values()):
            self.move_to_common(self.android_abis[0], path)
            for abi in self.android_abis[1:]:
                abi_path = join(self.target, abi, path)
                if isdir(abi_path):
                    rmtree(abi_path)
                else:
                    os.remove(abi_path)
                try:
                    os.removedirs(dirname(abi_path))
                except OSError:
                    pass  # Directory is not empty.

        # If an ABI directory ended up empty, os.removedirs or os.renames will have deleted it.
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


def tree_add_path(tree, path, value):
    dir_name, base_name = os.path.split(path)
    subtree = tree
    if dir_name:
        for name in dir_name.split("/"):
            subtree = subtree.setdefault(name, {})
            assert isinstance(subtree, dict), path  # If `name` exists, it must be a directory.
    set_value = subtree.setdefault(base_name, value)
    assert (set_value is value), path  # `path` must not already exist.


def tree_remove_path(tree, path):
    dir_name, base_name = os.path.split(path)
    subtree = tree
    if dir_name:
        for name in dir_name.split("/"):
            try:
                subtree = subtree[name]
            except KeyError:
                raise ValueError("Directory not found: '{}' in '{}'".format(name, path))
    try:
        del subtree[base_name]
    except KeyError:
        raise ValueError("Path not found: " + path)


def tree_merge_from(dst_tree, src_tree):
    assert isinstance(src_tree, dict), src_tree  # Prevent overwriting a file, or merging a
    assert isinstance(dst_tree, dict), dst_tree  # file with a directory,
    for name, src_value in six.iteritems(src_tree):
        dst_value = dst_tree.get(name)
        if dst_value is None:
            # Need to copy, otherwise later changes to one tree would also affect the other.
            dst_tree[name] = deepcopy(src_value)
        else:
            tree_merge_from(dst_value, src_value)


# Returns a list of paths which are recursively identical in all trees.
def common_paths(*trees):
    def process_subtrees(subtrees, prefix):
        for name in subtrees[0]:
            values = [t.get(name) for t in subtrees]
            if all(values[0] == v for v in values[1:]):
                result.append(join(prefix, name))
            elif all(isinstance(v, dict) for v in values):
                process_subtrees(values, join(prefix, name))

    result = []
    process_subtrees(trees, "")
    return result


class ReqFileAppend(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        getattr(namespace, self.dest).extend(["-r", value])


class CommandError(Exception):
    pass


if __name__ == "__main__":
    PipInstall().main()
