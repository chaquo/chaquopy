"""Copyright (c) 2018 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

import os
from os.path import exists, join
import sys
import traceback
from . import stream, importer


def initialize(context, build_json, app_path):
    stream.initialize()
    initialize_stdlib(context)
    importer.initialize(context, build_json, app_path)


def initialize_stdlib(context):
    # OpenSSL actually does know the location of the system CA store on Android, but
    # unfortunately there are multiple incompatible formats of that location, so we can't rely
    # on it (https://blog.kylemanna.com/android/android-ca-certificates/).
    os.environ["SSL_CERT_FILE"] = join(str(context.getFilesDir()), "chaquopy/cacert.pem")

    # argv defaults to not existing, which may crash some programs.
    sys.argv = [""]

    # executable defaults to "python" on 2.7, or "" on 3.6. But neither of these values (or
    # None, which is mentioned in the documentation) will allow platform.platform() to run
    # without crashing.
    try:
        sys.executable = os.readlink("/proc/{}/exe".format(os.getpid()))
    except Exception:
        # Can't be certain that /proc will work on all devices, so try to carry on.
        traceback.print_exc()
        sys.executable = ""

    # Remove default paths (#5410).
    invalid_paths = [p for p in sys.path
                     if not (exists(p) or p.startswith(importer.ASSET_PREFIX))]
    for p in invalid_paths:
        sys.path.remove(p)

    # tempfile
    tmpdir = join(str(context.getCacheDir()), "chaquopy/tmp")
    if not exists(tmpdir):
        os.makedirs(tmpdir)
    os.environ["TMPDIR"] = tmpdir
