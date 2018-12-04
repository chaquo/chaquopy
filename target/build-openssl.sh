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

# Adding `-j` to the make command has no effect because of the way it uses recursive make. This
# may be fixed in OpenSSL 1.1.0: see https://github.com/openssl/openssl/issues/298 ("jobserver
# unavailable") and https://github.com/openssl/openssl/issues/5762.
make

tmp_dir="/tmp/openssl-$$"
make install_sw INSTALL_PREFIX=$tmp_dir
tmp_prefix="$tmp_dir/usr/local/ssl"
prefix="$sysroot/usr"
cp -af $tmp_prefix/include/* $prefix/include
cp -af $tmp_prefix/lib/*.so* $prefix/lib
rm -rf $tmp_dir
