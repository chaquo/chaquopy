#!/bin/bash
set -eu

./configure --host=$CHAQUOPY_TRIPLET --prefix=$PREFIX
make -j $CPU_COUNT
make install

if [ -d $PREFIX/lib64 ]; then
    mv $PREFIX/lib64/* $PREFIX/lib
    rmdir $PREFIX/lib64
fi

# rm $PREFIX/lib/libffi.{a,la}
rm $PREFIX/lib/libffi.la
rm -r $PREFIX/lib/pkgconfig
rm -r $PREFIX/share
