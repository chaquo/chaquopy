# Based on the file of the same name in cibuildwheel. Changes are marked with the word
# "Chaquopy".
#
# This module is called by the correpsonding .pth file. It does nothing unless the
# CIBW_HOST_TRIPLET environment variable is set, in which case it will monkey patch the
# process to simulate Android.

import collections
import os
import platform
import sys
import sysconfig
from typing import Any
import warnings


def initialize() -> None:
    if not (host_triplet := os.environ.get("CIBW_HOST_TRIPLET")):
        return

    # Chaquopy: do not monkey patch any subprocesses, including recursive calls to pip
    # to install the build environment, or calls to the PEP 517 backend.
    del os.environ["CIBW_HOST_TRIPLET"]

    # Chaquopy: initialize sysconfig before applying any monkey patches, otherwise it'll
    # try to load the Android sysconfigdata, which isn't available in this context.
    sysconfig.get_config_vars()

    # os ######################################################################
    def cross_os_uname() -> os.uname_result:
        # Chaquopy: added 32-bit support.
        machine = host_triplet.split("-")[0]
        if machine == "arm":
            machine = "armv7l"

        return os.uname_result(
            (
                "Linux",
                "localhost",
                # The Linux kernel version and release are unlikely to be significant, but return
                # realistic values anyway (from an API level 24 emulator).
                "3.18.91+",
                "#1 SMP PREEMPT Tue Jan 9 20:35:43 UTC 2018",
                machine,
            )
        )

    os.name = "posix"
    os.uname = cross_os_uname

    # platform ################################################################
    #
    # Chaquopy: added support for Python 3.12 and older.
    AndroidVer = collections.namedtuple(
        "AndroidVer", "release api_level manufacturer model device is_emulator"
    )

    # We can't determine the user-visible Android version number from the API level, so return a
    # string which will work fine for display, but will fail to parse as a version number.
    def cross_android_ver(*args: Any, **kwargs: Any) -> AndroidVer:
        return AndroidVer(
            release=f"API level {cross_getandroidapilevel()}",
            api_level=cross_getandroidapilevel(),
            manufacturer="Google",
            model="sdk_gphone64",
            device="emu64",
            is_emulator=True,
        )

    platform.android_ver = cross_android_ver

    if sys.version_info < (3, 13):
        def cross_platform_uname():
            os_uname = cross_os_uname()
            return platform.uname_result(
                "Android",
                os_uname.nodename,
                cross_android_ver().release,
                os_uname.version,
                os_uname.machine,
            )

        platform.uname = cross_platform_uname

    else:
        # platform.uname is implemented in terms of platform.android_ver.
        pass

    # sys #####################################################################
    def cross_getandroidapilevel() -> int:
        # Chaquopy: use an environment variable rather than the sysconfigdata.
        return int(os.environ["ANDROID_API_LEVEL"])

    # Some packages may recognize sys.cross_compiling from the crossenv tool.
    sys.cross_compiling = True  # type: ignore[attr-defined]
    sys.getandroidapilevel = cross_getandroidapilevel  # type: ignore[attr-defined]
    sys.implementation._multiarch = host_triplet  # type: ignore[attr-defined]
    sys.platform = "android"

    # Chaquopy: removed anything to do with the Android sysconfigdata, which isn't
    # available in this context, and shouldn't be necessary since we're not actually
    # doing any native builds.

    # sysconfig ###############################################################
    #
    # Chaquopy: added support for Python 3.12 and older.
    if sys.version_info < (3, 13):
        def cross_get_platform():
            abi = {
                "x86_64": "x86_64",
                "i686": "x86",
                "aarch64": "arm64_v8a",
                "armv7l": "armeabi_v7a",
            }[platform.machine()]
            return f"android-{cross_getandroidapilevel()}-{abi}"

        sysconfig.get_platform = cross_get_platform

        if sys.version_info < (3, 12):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                import distutils.util
                distutils.util.get_platform = cross_get_platform

    else:
        # get_platform is implemented in terms of sys.platform,
        # sysconfig.get_config_var("ANDROID_API_LEVEL"), and os.uname.
        pass
