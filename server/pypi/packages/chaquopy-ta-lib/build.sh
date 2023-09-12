#!/bin/bash
set -eu

./configure --host=$HOST --prefix=$PREFIX
make  # The build breaks with -j.
make install

rm -r $PREFIX/bin
rm -r $PREFIX/lib/*.la
