#!/bin/bash
set -eu

HOST_TRIPLET=$(basename $CC | sed 's/-gcc$//')
./configure --host=$HOST_TRIPLET --prefix=$PREFIX
make  # The build breaks with -j.
make install

rm -r $PREFIX/bin
rm -r $PREFIX/lib/*.la
