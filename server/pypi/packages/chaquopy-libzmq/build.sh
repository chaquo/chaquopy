#!/bin/bash
set -eu

HOST_TRIPLET=$(basename $CC | sed 's/-gcc$//')

./configure --host=$HOST_TRIPLET
make -j $CPU_COUNT
make install prefix=$PREFIX

rm $PREFIX/lib/*.a
rm -r $PREFIX/share/man
