#!/bin/bash
set -eu

host_triplet=$(basename $CC | sed 's/-gcc$//')

export LIBXML_CFLAGS="-I$(pwd)/../requirements/chaquopy/include"
export LIBXML_LIBS="-L$(pwd)/../requirements/chaquopy/lib -lxml2"
./configure --host=$host_triplet --prefix=$PREFIX --without-python
make -j $CPU_COUNT V=1
make install

rm -r $PREFIX/{bin,share}
rm -r $PREFIX/lib/{*.a,*.la,*.sh,pkgconfig}
