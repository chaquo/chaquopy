#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
toolchain=$(realpath ${1:?})

cd $target_dir
. build-common.sh

# TODO: when building for x86, we may need the patch from
# https://github.com/buffer51/android-gfortran#other-targets--hosts. It's not clear whether
# this has been fixed in newer versions of GCC.

mkdir gcc-build
cd gcc-build
export PATH=$PATH:$toolchain/bin  # For target assembler and linker.
config_args="--target=$host_triplet --with-sysroot=$sysroot --enable-languages=c,fortran"  # FIXME remove `c`?

# Not simply using `--enable-shared`, because this would also enable a shared libgcc
# (libgcc_s.so), which has the surprising effect of causing the static libgcc.a to have some
# things removed from it:
#
# * "Unwinding" logic for C++ exception handlers.
#
# * Thread-local storage emulation (emutls), which is required on Android to work around
#   limitations in the dynamic linker (https://bugs.llvm.org/show_bug.cgi?id=23566#c4 and
#   https://stackoverflow.com/a/27195324).
#
# These things are moved to a separate file libgcc_eh.a, intended for linking into an
# executable build, on the basis that they should only exist once per program (see
# https://gcc.gnu.org/ml/gcc/2012-03/msg00104.html, and LIB2ADDEH in libgcc/Makefile.in).
#
# We could package libgcc_s.so somehow, but the fact that the Google NDK has never included it
# implies that it's safe to use the static libgcc.a, and have a separate copy of these things
# in each library, as long as all the copies are the same. This is confirmed by an NDK
# developer in the case of the unwinder
# (https://github.com/android-ndk/ndk/issues/289#issuecomment-289170461). I can't find a clear
# answer for the case of emultls, but I think it's implied by the same developer's statement
# that the Google NDK's GCC does support this feature (StackOverflow link above),
config_args+=" --enable-shared=libgfortran"

# libquadmath isn't available for ARM, so be consistent and disable it on all ABIs. This also
# prevents the build system from giving libgfortran a RUNPATH entry pointing at the temporary
# build directory. RUNPATH is recognized by Android API level 24 and later
# (https://github.com/aosp-mirror/platform_bionic/blob/master/android-changes-for-ndk-developers.md),
# but would probably be harmless since it won't exist anyway.
config_args+=" --disable-libquadmath --disable-libquadmath-support"

../gcc/configure $config_args

make -j $(nproc)

# FIXME install:
#
# don't overwrite any existing files
#
# If --with-sysroot "is a subdirectory of ${exec_prefix}, then it will be found relative to the
# GCC binaries if the installation tree is moved." Does the same apply to lib/gcc?
#
# rm -r gcc-build
