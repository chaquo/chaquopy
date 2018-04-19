#!/bin/bash
set -eu

mkdir -p $PREFIX/lib
TOOLCHAIN_LIB=$(dirname $CC)/../*/lib

cp $TOOLCHAIN_LIB/libgfortran.so.3 $PREFIX/lib

# TODO: remove so both ABIs are consistent.
if [ -f  $TOOLCHAIN_LIB/libquadmath.so.0 ]; then
    cp $TOOLCHAIN_LIB/libquadmath.so.0 $PREFIX/lib
fi

for file in $PREFIX/lib/*; do
    # patchelf rearranges the file in ways that break some other tools, including strip
    # (https://github.com/NixOS/patchelf/issues/10). Stripping before patching works on API
    # level 26, but level 15 gives a dynamic linker error even when not stripping at all
    # ("get_lib_extents[777]: 1132 - No loadable segments found").
    #
    # toolchain-strip --strip-unneeded $file

    # In libgfortran only, our build process sets a RUNPATH of
    # `/tmp/ndk-smith/build/toolchain/prefix/i686-linux-android/lib` (#5409).
    patchelf --remove-rpath $file

    # Both libraries lack this DT_NEEDED entry, despite requiring symbols which only libcrystax
    # provides, e.g. _DefaultRuneLocale (#5409).
    patchelf --add-needed libcrystax.so $file
done
