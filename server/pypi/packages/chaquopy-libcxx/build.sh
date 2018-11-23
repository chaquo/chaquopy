#!/bin/bash
set -eu

toolchain=$(realpath $(dirname $CC)/..)

header_version=$(cat $toolchain/include/c++/*/__libcpp_version)
if [[ $header_version != $PKG_VERSION ]]; then
    echo "Header version '$header_version' doesn't match meta.yaml version '$PKG_VERSION'"
    exit 1
fi

mkdir -p $PREFIX/lib
cp $toolchain/*/lib/libc++_shared.so $PREFIX/lib
