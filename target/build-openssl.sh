#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
toolchain=$(realpath ${1:?})

cd $target_dir
. build-common.sh
. build-common-tools.sh

cd openssl
if [[ $(basename $toolchain) =~ '64$' ]]; then
    bits="64"
else
    bits="32"
fi
./Configure linux-generic$bits shared
make -j $(nproc)

tmp_dir="/tmp/openssl-$$"
make install_sw DESTDIR=$tmp_dir
tmp_prefix="$tmp_dir/usr/local"
prefix="$sysroot/usr"
cp -af $tmp_prefix/include/* $prefix/include
cp -af $tmp_prefix/lib/*.so* $prefix/lib
rm -rf $tmp_dir
