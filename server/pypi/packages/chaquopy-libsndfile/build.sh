#!/bin/bash
set -eu

./configure --host=$CHAQUOPY_TRIPLET --prefix=$PREFIX
make -j $CPU_COUNT
make install

rm -r $PREFIX/bin
# rm $PREFIX/lib/*.a
rm -r $PREFIX/share
