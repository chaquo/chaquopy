#!/bin/bash
set -eu

./configure --host=$HOST
make -j $CPU_COUNT
make install prefix=$PREFIX

find $PREFIX -type l | xargs rm

rm -r $PREFIX/bin

mv $PREFIX/include/libpng16/* $PREFIX/include
rmdir $PREFIX/include/libpng16

# Some versions of Android (e.g. API level 26) have a libpng.so in /system/lib, but our copy
# has an SONAME of libpng16.so, so there's no conflict.
rm -r $PREFIX/lib/{*.a,*.la,pkgconfig}

rm -r $PREFIX/share
