#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
toolchain=$(realpath ${1:?})

cd $target_dir
. build-common.sh
. build-common-tools.sh

build_dir="/tmp/openssl-build-$$"
rm -rf $build_dir
mkdir -p $build_dir
cd $build_dir

if [[ $(basename $toolchain) =~ '64' ]]; then
    bits="64"
else
    bits="32"
fi
$target_dir/openssl/Configure linux-generic$bits shared
make -j $(nproc)

install_dir="/tmp/openssl-install-$$"
rm -rf $install_dir
make install_sw DESTDIR=$install_dir
tmp_prefix="$install_dir/usr/local"
prefix="$sysroot/usr"
cp -af $tmp_prefix/include/* $prefix/include
cp -af $tmp_prefix/lib/*.so* $prefix/lib
rm -r $install_dir

rm -r $build_dir
