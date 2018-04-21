# Crystax NDK

Extract Crystax 10.3.2 to $CRYSTAX_DIR.

In the following, $ABIS is a comma-separated list of Android ABIs, e.g. "armeabi-v7a,x86".


# libcrystax build

libcrystax must be rebuilt to fix issue #5372 (Crystax issue #1455).

Clone the following Crystax repositories (those marked with * have Chaquopy-specific changes
and *must* be cloned from chaquo.com):

      vendor/dlmalloc
      vendor/freebsd
      vendor/libkqueue
      vendor/libpwq
      platform/bionic
    * platform/ndk
      platform/system/core
      toolchain/llvm-3.6/compiler-rt

Check them all out on the branch crystax-r10, then run the following commands. If building
armeabi-v7a, $ABIS here should also include armeabi and armeabi-v7a-hard, because
make-standalone-toolchain.sh copies them all into the same toolchain, in both thumb and
non-thumb builds, for a total of 6 variants. armeabi in particular is required for OpenBLAS:
see notes in server/pypi/packages/openblas.

    cd platform/ndk/sources/crystax
    NDK=$CRYSTAX_DIR ABIS=$ABIS make

Rename all the libcrystax.* files under $CRYSTAX_DIR/sources/crystax, and replace them with the
files just built in sources/crystax/libs


# OpenSSL build

Extract OpenSSL source to $OPENSSL_DIR (doesn't need to come from Crystax), then run this script:

    $CRYSTAX_DIR/build/tools/build-target-openssl.sh --verbose --abis=$ABIS $OPENSSL_DIR

The OpenSSL libraries and includes will now be in $CRYSTAX_DIR/sources/openssl/<version>. Copy the
Android.mk from sources/openssl/1.0.1p to this subdirectory.


# Python build

(TODO: merge our local copies of these files back into into our forked copy of
crystax/platform/ndk, just as we have with the GCC and libcrystax build processs. It looks like
build-target-python.sh can still be run in place using the --ndk-dir option.)

Extract Python source to $PYTHON_DIR (doesn't need to come from Crystax).

For Python 3.6 only, run the following commands, derived from
https://github.com/inclement/crystax_python_builds:

    cd target/crystax
    patch -t -d $PYTHON_DIR -p1 -i patch_python3.6.patch
    cp android.mk.3.6 config.c.3.6 interpreter.c.3.6 $CRYSTAX_DIR/build/tools/build-target-python
    mkdir $CRYSTAX_DIR/sources/python/3.6
    cp sources-Android.mk.3.6 $CRYSTAX_DIR/sources/python/3.6/Android.mk

Then:

    cd target/crystax
    export OPENSSL_VERSION=<version built above>
    ./build-target-python.sh --verbose --abis=$ABIS $PYTHON_DIR

The Python libraries and includes will now be in $CRYSTAX_DIR/sources/python. These should be
packaged for the Maven repository by package-target.sh. If adding a new Python x.y version,
they will also need to be copied to any other machines where Chaqupy itself is built.
