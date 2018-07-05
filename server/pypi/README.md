# GCC

If building OpenBLAS or SciPy, the Crystax GCC toolchain must be rebuilt to add support for
Fortran.

Clone the following Crystax repositories (those marked with * have Chaquopy-specific changes
and *must* be cloned from chaquo.com):

    * platform/development
    * platform/ndk
      toolchain/binutils
    * toolchain/build
      toolchain/cloog
    * toolchain/gcc/gcc-4.9
      toolchain/gdb/gdb-7.10
      toolchain/gmp
      toolchain/isl
      toolchain/mpc
      toolchain/mpfr
      toolchain/ppl
      toolchain/sed

Check them all out on the branch crystax-r10.

Install the following prerequisites on the build machine:

    bison
    flex
    m4
    texinfo

Run the following commands:

    cd platform/ndk
    ./build/tools/build-host-prebuilts.sh --verbose --systems=linux-x86_64 --arch=arm,x86 ../../toolchain

Rename the toolchains in your Crystax installation, and replace them with the toolchains just
built in platform/ndk/toolchains.


# libcrystax

Note that when building armeabi-v7a, make-standalone-toolchain.sh also copies armeabi and
armeabi-v7a-hard into the toolchain, in both thumb and non-thumb builds, for a total of 6
variants. armeabi in particular is required for OpenBLAS: see notes in
server/pypi/packages/openblas.

This includes libcrystax, which we've made changes to. However, the changes shouldn't affect
binary compatibility, so the armeabi and armeabi-v7a-hard libraries, which aren't present at
runtime, probably don't need to be rebuilt. If we do need to rebuild them, the process is in
target/README.md.


# Adding a new package

Create a new subdirectory in `packages`, containing the following:

* A `meta.yaml` file. This supports a subset of Conda syntax, defined in meta-schema.yaml.
* A `test.py` file (or `test` package), to run on a target installation. This should contain a
  unittest.TestCase subclass which imports the package and does some basic checks.
* For non-Python packages, a `build.sh` script. See build-wheel.py for environment variables
  which are available to it.
* If necessary, a `patches` subdirectory containing patch files.

Run build-wheel.py once for each desired combination of package version, Python version and ABI.

Copy the resulting wheels from packages/*/dist to a private package repository.

Test with pkgtest app for both Python 2 and 3 on:
* minSdkVersion emulator, or API 18 if "too many libraries" error occurs (#5316).
* targetSdkVersion emulator
* Any ARM device

Once everything's working, move the wheels to the public package repository.

Update any GitHub issues.

Email any affected users, including anyone who commented or gave a thumbs up to a related issue
either on our tracker or Kivy's.
