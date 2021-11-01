#!/bin/bash
set -eu

HOST_TRIPLET=$(basename $CC | sed 's/-gcc$//')

./configure --host=$HOST_TRIPLET --disable-static --disable-openmp --disable-examples
make -j $CPU_COUNT
make install prefix=$PREFIX

rm -rf $PREFIX/{bin,share}
