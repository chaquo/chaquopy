#!/bin/bash
set -eu

./configure --host=$HOST
make -j $CPU_COUNT
make install prefix=$PREFIX

rm -r $PREFIX/bin
rm $PREFIX/lib/*.a
rm -r $PREFIX/share/man