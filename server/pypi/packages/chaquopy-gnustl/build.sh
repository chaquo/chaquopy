#!/bin/bash
set -eux

mkdir -p $PREFIX/lib

# build-wheel renames it to libstdc++.so so the compiler will find it, but its SONAME is
# libgnustl_shared.so.
cp $(dirname $CC)/../*/lib*/$CHAQUOPY_ABI_VARIANT/libstdc++.so $PREFIX/lib/libgnustl_shared.so
