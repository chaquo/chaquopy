#!/bin/bash
set -eu

./configure --host=$CHAQUOPY_TRIPLET --prefix=$PREFIX --without-python
make -j $CPU_COUNT
make install

rm -r $PREFIX/{bin,share}
# rm -r $PREFIX/lib/{*.a,*.la,*.sh}
rm -r $PREFIX/lib/{*.la,*.sh}
