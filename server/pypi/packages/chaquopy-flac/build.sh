#!/bin/bash
set -eu

./configure --host=$HOST --prefix=$PREFIX
make -j $CPU_COUNT
make install

rm -r $PREFIX/share
