# Introduction

This file contains instructions for building and packaging Python and its dependencies for use
with Chaquopy. This process has only been tested on Linux x86-64.

In the following, let `$ABIS` be a comma-separated list of Android ABI names, e.g.
`armeabi-v7a,x86`.


# Crystax NDK

Install Crystax NDK 10.3.2. Let its location be `$CRYSTAX_DIR`.

We've made changes to the Crystax build scripts, so instead of running them from the NDK
itself, we'll run them from the modified source repository.

Clone the `crystax-platform-ndk` repository from Chaquo, into a directory called
`platform/ndk`.

Check it out on the branch crystax-r10.


# libcrystax

libcrystax must be rebuilt to fix issue #5372 (Crystax issue #1455).

Clone the following Crystax repositories from [GitHub](https://github.com/crystax/) into the
same directory structure as `platform/ndk`. Except where indicated, the GitHub repository names
are formed by taking the directory names and replacing '/' with '-'.

    platform/bionic
    platform/system/core
    toolchain/llvm-3.6/compiler-rt  [from android-toolchain-compiler-rt-3-6]
    vendor/dlmalloc
    vendor/freebsd
    vendor/libkqueue
    vendor/libpwq

Check all these repositories out on the branch crystax-r10.

Then run the following:

    cd platform/ndk/sources/crystax
    NDK=$CRYSTAX_DIR ABIS=$ABIS make
    cd libs
    for file in $(find -name '*.a' -or -name '*.so'); do cp $file $CRYSTAX_DIR/sources/crystax/libs/$file; done


# OpenSSL

Crystax doesn't supply a pre-built OpenSSL, so we have to build it ourselves.

Download and extract OpenSSL source, of the version given as `OPENSSL_VERSIONS` in
`platform/ndk/build/tools/dev-defaults.sh`. Let its location be `$OPENSSL_DIR`. Then run the
following:

    platform/ndk/build/tools/build-target-openssl.sh --verbose --ndk-dir=$CRYSTAX_DIR --abis=$ABIS $OPENSSL_DIR

The OpenSSL libraries and includes will now be in `$CRYSTAX_DIR/sources/openssl/<version>`.


# SQLite

Crystax's pre-built library is used. No action is required.


# Python

Download and extract Python source, of a [version supported by
Chaquopy](https://chaquo.com/chaquopy/doc/current/android.html#python-version). Let its
location be `$PYTHON_DIR`. . Then run the following:

    platform/ndk/build/tools/build-target-python.sh --verbose --ndk-dir=$CRYSTAX_DIR --abis=$ABIS $PYTHON_DIR

The Python libraries and includes will now be in `$CRYSTAX_DIR/sources/python/<version>`.


# Packaging and distribution

Run the following:

    package-target.sh $CRYSTAX_DIR <major.minor> <micro-build> <target>

Where:

* `package-target.sh` is in the same directory as this README.
* `<major.minor>` is the first part of the Python version, e.g. `3.6`.
* `<micro-build>` is the last part of the Python version, and the build number used for that
  version by the current version of Chaquopy, separated by a hyphen, e.g. `5-4`
* `<target>` is the path of the directory to output to, e.g.
  `/path/to/com/chaquo/python/target`.

A new version subdirectory will be created within the target directory, and the following files
will be created there:

* One ZIP for each ABI, containing native libraries and modules.
* Two ZIPs for the Python standard library: one in `.py` format and one in `.pyc` format.

See the [Chaquopy Maven repository](https://chaquo.com/maven/com/chaquo/python/target/) for
examples of this script's output.
