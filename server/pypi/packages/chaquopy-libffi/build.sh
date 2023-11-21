#!/bin/bash
set -eu

./configure --host=$HOST --prefix=$PREFIX
make -j $CPU_COUNT
make install

if [ -d $PREFIX/lib64 ]; then
    mv $PREFIX/lib64/* $PREFIX/lib
    rmdir $PREFIX/lib64
fi

rm $PREFIX/lib/*.a
rm -r $PREFIX/share
