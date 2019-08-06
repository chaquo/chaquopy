#!/bin/bash
set -eu

HOST_TRIPLET=$(basename $CC | sed 's/-gcc$//')

# Configure command based on coincurve's setup.py.
./autogen.sh
./configure --host=$HOST_TRIPLET --enable-shared --disable-static \
            --disable-dependency-tracking --with-pic --enable-module-recovery --disable-jni \
            --enable-experimental --enable-module-ecdh --enable-benchmark=no
make -j $CPU_COUNT
make install prefix=$PREFIX

rm -r $PREFIX/lib/{*.la,pkgconfig}
