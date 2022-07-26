#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
toolchain=$(realpath ${1:?})

cd $target_dir
. build-common.sh
. build-common-tools.sh

version="5.2.4"
rm -rf xz-$version*
curl -OL https://tukaani.org/xz/xz-$version.tar.gz
tar -xf xz-$version.tar.gz

cd xz-$version
./configure --host=$host_triplet --prefix=$sysroot/usr --disable-shared --with-pic
make -j $(nproc)
make install

cd ..
rm -rf xz-$version*
