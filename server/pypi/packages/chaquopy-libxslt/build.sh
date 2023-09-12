#!/bin/bash
set -eu

./configure --host=$HOST --prefix=$PREFIX --without-crypto --without-python
make -j $CPU_COUNT V=1
make install

rm -r $PREFIX/{bin,share}
rm -r $PREFIX/lib/{*.a,*.la,*.sh}
