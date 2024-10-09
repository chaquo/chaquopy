#!/bin/bash
set -eu -o pipefail

toolchain=$(realpath $(dirname $AR)/..)

pattern='^ *# *define +_LIBCPP_VERSION +([0-9]+)$'
header_version=$(
    grep -E "$pattern" "$toolchain/sysroot/usr/include/c++/v1/__config" |
    sed -E "s/$pattern/\1/"
)
if [ "$header_version" != "$PKG_VERSION" ]; then
    echo "Header version '$header_version' doesn't match meta.yaml version '$PKG_VERSION'"
    exit 1
fi

mkdir -p $PREFIX/lib
cp $toolchain/sysroot/usr/lib/$HOST/libc++_shared.so $PREFIX/lib
