#!/bin/bash
set -eu

mkdir -p $PREFIX/lib
TOOLCHAIN_LIB=$(dirname $CC)/../*/lib

# build-wheel renames it to libstdc++.so so the compiler will find it, but its SONAME is
# libgnustl_shared.so.
cp $TOOLCHAIN_LIB/libstdc++.so $PREFIX/lib/libgnustl_shared.so
