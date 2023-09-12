#!/bin/bash
set -eu

./configure --host=$HOST --prefix=$PREFIX --without-python
make -j $CPU_COUNT
make install

rm -r $PREFIX/{bin,share}
rm -r $PREFIX/lib/{*.a,*.la,*.sh}
