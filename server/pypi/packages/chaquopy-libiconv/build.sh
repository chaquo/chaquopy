#!/bin/bash
set -eu

./configure --host=$CHAQUOPY_TRIPLET --prefix=$PREFIX --disable-static
make -j $CPU_COUNT
make install

rm -rf $PREFIX/share
