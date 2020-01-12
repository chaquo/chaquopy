#!/bin/bash
set -eu

toolchain=$(realpath $(dirname $CC)/..)

header_version=$(cat $toolchain/include/c++/*/__libcpp_version)
if [[ $header_version != $PKG_VERSION ]]; then
    echo "Header version '$header_version' doesn't match meta.yaml version '$PKG_VERSION'"
    exit 1
fi

case $CHAQUOPY_ABI in
    armeabi-v7a) subdir="lib/armv7-a/thumb" ;;
    x86_64)      subdir="lib64" ;;
    *)           subdir="lib" ;;
esac

mkdir -p $PREFIX/lib
cp $toolchain/*/$subdir/libc++_shared.so $PREFIX/lib
