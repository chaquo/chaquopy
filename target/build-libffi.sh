#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
toolchain=$(realpath ${1:?})

cd $target_dir
. build-common.sh
. build-common-tools.sh

version="3.2.1"
rm -rf libffi-$version*
wget ftp://sourceware.org/pub/libffi/libffi-$version.tar.gz
tar -xf libffi-$version.tar.gz
rm libffi-$version.tar.gz

cd libffi-$version
./configure --host=$host_triplet --prefix=$sysroot/usr
make -j $(nproc)

make install
mv $sysroot/usr/lib/libffi-$version/include/* $sysroot/usr/include
rm $sysroot/usr/lib/libffi.so*  # Shared library will not be available at runtime
