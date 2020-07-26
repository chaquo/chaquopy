#!/bin/bash
set -eu

HOST_TRIPLET=$(basename $CC | sed 's/-gcc$//')

./configure --host=$HOST_TRIPLET --prefix=$PREFIX
make -j $CPU_COUNT
make install

rm -r $PREFIX/share
