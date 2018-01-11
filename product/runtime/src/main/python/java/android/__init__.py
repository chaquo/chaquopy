"""Copyright (c) 2018 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

import os
from os.path import exists, join
from . import stream, importer


def initialize(context, app_path):
    stream.initialize()

    # For tempfile module.
    tmpdir = join(str(context.getCacheDir()), "chaquopy/tmp")
    if not exists(tmpdir):
        os.makedirs(tmpdir)
    os.environ["TMPDIR"] = tmpdir

    importer.initialize(context, app_path)
