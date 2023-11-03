#!/bin/bash
set -eu

RESOLVED_CC=$($CC -print-prog-name=clang)
toolchain=$(realpath $(dirname $RESOLVED_CC)/..)

actual_version=$(printf "#include <ciso646>\nint main () {}" | $CC -E -stdlib=libc++ -x c++ -dM - | grep -w "#define _LIBCPP_VERSION" | cut -d' ' -f3)
# actual_version=$(cat $toolchain/sysroot/usr/include/c++/v1/__libcpp_version)
if [[ $actual_version != $PKG_VERSION ]]; then
    echo "Actual version '$actual_version' doesn't match meta.yaml version '$PKG_VERSION'"
    exit 1
fi

mkdir -p $PREFIX/lib
cp $toolchain/sysroot/usr/lib/$HOST/libc++_shared.so $PREFIX/lib
