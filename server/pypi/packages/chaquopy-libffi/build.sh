#!/bin/bash
set -eu

HOST_TRIPLET=$(basename $CC | sed 's/-gcc$//')

./configure --host=$HOST_TRIPLET --prefix=$PREFIX
make -j $CPU_COUNT
make install

if [ -d $PREFIX/lib64 ]; then
    mv $PREFIX/lib64/* $PREFIX/lib
    rmdir $PREFIX/lib64
fi

rm $PREFIX/lib/libffi.{a,la}
rm -r $PREFIX/lib/pkgconfig
rm -r $PREFIX/share
