#!/bin/bash
set -eu

HOST_TRIPLET=$(basename $CC | sed 's/-gcc$//')
# SIMD is only available for x86, so disable for consistency between ABIs.
./configure --host=$HOST_TRIPLET --without-turbojpeg --without-simd
make -j $CPU_COUNT
make install prefix=$PREFIX

rm -r $PREFIX/{bin,doc,man}
mv $PREFIX/lib32 $PREFIX/lib
mv $PREFIX/lib/libjpeg.so $PREFIX/lib/libjpeg_chaquopy.so  # See patches/soname.patch
rm -r $PREFIX/lib/{*.a,*.la,pkgconfig}
