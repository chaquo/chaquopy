#!/bin/bash
set -eu

./configure --host=$CHAQUOPY_TRIPLET --prefix=$PREFIX
make  # The build breaks with -j.
make install

rm -r $PREFIX/bin
rm -r $PREFIX/lib/*.la
