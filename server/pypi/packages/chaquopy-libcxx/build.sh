#!/bin/bash
set -eu

toolchain=$(realpath $(dirname $CC)/..)

header_version=$(cat $toolchain/sysroot/usr/include/c++/v1/__libcpp_version)
if [[ $header_version != $PKG_VERSION ]]; then
    echo "Header version '$header_version' doesn't match meta.yaml version '$PKG_VERSION'"
    exit 1
fi

mkdir -p $PREFIX/lib
cp $toolchain/sysroot/usr/lib/$CHAQUOPY_TRIPLET/libc++_shared.so $PREFIX/lib
