# Introduction

This file contains instructions for building and packaging Python and its dependencies for use
with Chaquopy. This process has only been tested on Linux x86-64. However, the resulting
packages can be used on any supported Android build platform (Windows, Linux or Mac).

In the following, let `$ABIS` be a comma-separated list of Android ABI names, e.g.
`armeabi-v7a,x86`.


# Build prerequisites

* Python of the same major.minor version as the one you're building
* GNU make
* Ruby
* [Crystax NDK](https://www.crystax.net/en/download) version 10.3.2 (let its location be
  `$CRYSTAX_DIR`)

Check out the submodule `crystax/platform/ndk`. This contains modified copies of some of the
Crystax build scripts.


# libcrystax

The libcrystax released in Crystax 10.3.2 contains several bugs, so we must rebuild it (see
commit history of `crystax/platform/ndk`).

Check out the following submodules under `crystax`:

    platform/bionic
    platform/system/core
    toolchain/llvm-3.6/compiler-rt
    vendor/dlmalloc
    vendor/freebsd
    vendor/libkqueue
    vendor/libpwq

Then run the following:

    cd crystax/platform/ndk/sources/crystax
    NDK=$CRYSTAX_DIR ABIS=$ABIS make
    cd libs
    for file in $(find -name '*.a' -or -name '*.so'); do cp $file $CRYSTAX_DIR/sources/crystax/libs/$file; done


# OpenSSL

Crystax doesn't supply a pre-built OpenSSL, so we have to build it ourselves.

Check out the submodule `openssl`: its tag (as shown by `git submodule status`) should match
`OPENSSL_VERSIONS` in `crystax/platform/ndk/build/tools/dev-defaults.sh`. Let its location be
`$OPENSSL_DIR`. Then run the following:

    crystax/platform/ndk/build/tools/build-target-openssl.sh --verbose --ndk-dir=$CRYSTAX_DIR --abis=$ABIS $OPENSSL_DIR

The OpenSSL libraries and includes will now be in `$CRYSTAX_DIR/sources/openssl/<version>`.


# SQLite

Crystax's pre-built library is used. No action is required.


# Python

Check out the submodule `python`: its tag (as shown by `git submodule status`) should match the
[version you want to use with
Chaquopy](https://chaquo.com/chaquopy/doc/current/android.html#python-version). Let its
location be `$PYTHON_DIR`. . Then run the following:

    crystax/platform/ndk/build/tools/build-target-python.sh --verbose --ndk-dir=$CRYSTAX_DIR --abis=$ABIS $PYTHON_DIR

The Python libraries and includes will now be in `$CRYSTAX_DIR/sources/python/<version>`.


# Packaging and distribution

Run the following:

    package-target.sh $CRYSTAX_DIR <major.minor> <micro-build> <target>

Where:

* `package-target.sh` is in the same directory as this README.
* `<major.minor>` is the first part of the Python version, e.g. `3.6`.
* `<micro-build>` is the last part of the Python version, and the build number used for that
  version by the current version of Chaquopy, as specified in
  `product/buildSrc/src/main/java/com/chaquo/python/Common.java`. Separate them with a hyphen,
  e.g. `5-4` for Python 3.6.5 (as of Chaquopy 3.3.0).
* `<target>` is the path of the Maven directory to output to (see the top-level README). For
  example, `/path/to/maven/com/chaquo/python/target`.

A new version subdirectory will be created within the target directory, and the following files
will be created there:

* One ZIP for each ABI, containing native libraries and modules.
* Two ZIPs for the Python standard library: one in `.py` format and one in `.pyc` format.
