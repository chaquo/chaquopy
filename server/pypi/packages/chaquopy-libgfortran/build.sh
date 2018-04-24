#!/bin/bash
set -eux

mkdir -p $PREFIX/lib
cp $(dirname $CC)/../*/lib/$CHAQUOPY_ABI_VARIANT/libgfortran.so.3 $PREFIX/lib

# The most recently-released version of patchelf (0.9) rearranges the file in ways that break
# some other tools, including strip (https://github.com/NixOS/patchelf/issues/10). Stripping
# before patching works on API level 26, but level 15 gives a dynamic linker error even when
# the file isn't stripped at all ("get_lib_extents[777]: 1132 - No loadable segments found").
#
# There is an unreleased fix for this (https://github.com/NixOS/patchelf/pull/117). It has a
# known bug (https://github.com/NixOS/patchelf/pull/127), but that seems to apply only to
# executable files so isn't relevant to us.
#
# To install the fixed version, first uninstall nay existing version, then do the following
# (from https://github.com/pypa/manylinux/blob/6eae41b6988f34401d87d22fcb78970df2c3a06d/docker/build_scripts/build.sh):
#
#     apt-get install autoconf
#     PATCHELF_COMMIT=6bfcafbba8d89e44f9ac9582493b4f27d9d8c369
#     curl -sL -o patchelf.tar.gz https://github.com/NixOS/patchelf/archive/$PATCHELF_COMMIT.tar.gz
#     tar -xzf patchelf.tar.gz
#     (cd patchelf-$PATCHELF_COMMIT && ./bootstrap.sh && ./configure && make && make install)
PATCHELF_VERSION="$(patchelf --version)"
if [ "$PATCHELF_VERSION" != "patchelf 0.10" ]; then
    echo "$PATCHELF_VERSION is not the correct version: see comment in chaquopy-libgfortran/build.sh."
    exit 1
fi

# The library lacks this DT_NEEDED entry, despite requiring symbols which only libcrystax
# provides, e.g. _DefaultRuneLocale (#5409). This is because build-host-prebuilts.sh and
# build-gcc.sh originally didn't build any shared libraries at all from the GCC source tree,
# instead providing separate scripts such as build-gnu-libstdc++.sh, where -lcrystax *is*
# specified.
patchelf --add-needed libcrystax.so $PREFIX/lib/libgfortran.so.3
