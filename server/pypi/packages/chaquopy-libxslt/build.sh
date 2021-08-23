#!/bin/bash
set -eu

host_triplet=$(basename $CC | sed 's/-gcc$//')
./configure --host=$host_triplet --prefix=$PREFIX --without-python
make -j $CPU_COUNT V=1
make install

rm -r $PREFIX/{bin,share}
rm -r $PREFIX/lib/{*.a,*.la,*.sh}
