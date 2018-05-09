# Crystax NDK

Install Crystax 10.3.2. Let its location be $CRYSTAX_DIR.

In the following, $ABIS is a comma-separated list of Android ABIs, e.g. "armeabi-v7a,x86".

Clone the following Crystax repository from the Chaquo fork:

      platform/ndk

Check it out on the branch crystax-r10. Wherever `platform/ndk` appears below, use this
directory.


# libcrystax

libcrystax must be rebuilt to fix issue #5372 (Crystax issue #1455).

Clone the following Crystax repositories into the same directory structure as platform/ndk:

      vendor/dlmalloc
      vendor/freebsd
      vendor/libkqueue
      vendor/libpwq
      platform/bionic
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
files just built in platform/ndk/sources/crystax/libs.


# OpenSSL

Download and extract OpenSSL source, of the version specified in
platform/ndk/build/tools/dev-defaults.sh. Let its location be $OPENSSL_DIR. Then run this
script:

    platform/ndk/build/tools/build-target-openssl.sh --verbose --ndk-dir=$CRYSTAX_DIR \
        --abis=$ABIS $OPENSSL_DIR

The OpenSSL libraries and includes will now be in $CRYSTAX_DIR/sources/openssl/<version>. Copy the
Android.mk from sources/openssl/1.0.1p to this subdirectory.


# SQLite

Crystax's pre-built library is used. No action is required.


# Python

Download and extract Python source. Let its location be $PYTHON_DIR. Then run this script:

    platform/ndk/build-target-python.sh --verbose --ndk-dir=$CRYSTAX_DIR --abis=$ABIS $PYTHON_DIR

The Python libraries and includes will now be in $CRYSTAX_DIR/sources/python.


# Packaging and distribution

Run package-target.sh. (TODO: more detailed instructions required)

If adding a new Python x.y version, Python libraries and includes will also need to be copied
to any other machines where Chaquopy itself is built. (TODO: more detailed instructions required)
