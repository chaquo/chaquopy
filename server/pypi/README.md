# Introduction

This directory contains processes to build various native Python packages for use with
Chaquopy. The build process has only been tested on Linux x86-64. However, the resulting
packages can be used on any supported Android build platform (Windows, Linux or Mac).

All of these packages, as well as external non-Python libraries which they depend on,
are packaged as wheel files by the `build-wheel.py` script. Install the requirements in
`requirements.txt`, then run `build-wheel.py --help` for more information.


# Adding a new package

Create a new subdirectory in `packages`, containing the following:

* A `meta.yaml` file. This supports a subset of Conda syntax, defined in `meta-schema.yaml`.
* A `test.py` file (or `test` package), to run on a target installation. This should contain a
  unittest.TestCase subclass which imports the package and does some basic checks.
* For non-Python packages, a `build.sh` script. See `build-wheel.py` for environment variables
  which are passed to it.
* If necessary, a `patches` subdirectory containing patch files.

Run `build-wheel.py` once for each desired combination of package version, Python version and
ABI.

Copy the resulting wheels from `packages/<subdir>/dist` to a private package repository (edit
`--extra-index-url` in `pkgtest/app/build.gradle` if necessary).

Temporarily add the new package to `pkgtest/app/build.gradle`. If planning to
release the package before the next version of the SDK, also temporarily edit
`pkgtest/build.gradle` to test with the current released version.

Then test the app on the following devices, with at least one device being a clean install:

* minSdkVersion emulator, or API 18 if "too many libraries" error occurs (#5316)
* targetSdkVersion emulator
* Any armeabi-v7a device
* Any arm64-v8a device

Once everything's working, move the wheels to the public package repository, and go through the
public release procedure.


# GCC

If building OpenBLAS or SciPy, the Crystax GCC toolchain must be rebuilt to add support for
Fortran. If building anything else, there's no need to do this.

Check out the following submodules under `target/crystax`:

    platform/development
    platform/ndk
    toolchain/binutils
    toolchain/build
    toolchain/cloog
    toolchain/gcc/gcc-4.9
    toolchain/gdb/gdb-7.10
    toolchain/gmp
    toolchain/isl
    toolchain/mpc
    toolchain/mpfr
    toolchain/ppl
    toolchain/sed

Install the following prerequisites on the build machine:

    bison
    flex
    m4
    texinfo

Run the following commands:

    cd target/crystax/platform/ndk
    ./build/tools/build-host-prebuilts.sh --verbose --systems=linux-x86_64 --arch=arm,x86 ../../toolchain

The new toolchains will now be in `target/crystax/platform/ndk/toolchains`. Use these to
replace the toolchains in your Crystax installation.


# libcrystax notes

We've made some bug-fixes to libcrystax (see `target/README.md`), and we may make more in the
future. However, these shouldn't affect binary compatibility, so there's no need to rerun
`build-wheel.py --build-toolchain` whenever libcrystax changes.

Similarly, it doesn't matter that `build-wheel.py --build-toolchain` installs all variants of
libcrystax (e.g. armeabi (v5) and armeabi-v7a-hard), even though we're only rebuilding the ones
which we actually distribute. This is relevant to OpenBLAS because it actually builds in
armeabi (v5) mode: see `packages/chaquopy-openblas/build.sh`.
