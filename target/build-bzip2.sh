#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
toolchain=$(realpath ${1:?})

cd $target_dir
. build-common.sh
. build-common-tools.sh

version="1.0.8"
rm -rf bzip2-$version*
curl -OL https://sourceware.org/pub/bzip2/bzip2-$version.tar.gz
tar -xf bzip2-$version.tar.gz

cd bzip2-$version
# -e is needed to override explicit assignment to CC, CFLAGS etc. in the Makefile.
CFLAGS+=" -O2 -fPIC"
make -e -j $(nproc) bzip2 bzip2recover
make install PREFIX=$sysroot/usr

cd ..
rm -rf bzip2-$version*
