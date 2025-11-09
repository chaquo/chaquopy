#!/bin/bash
set -eu -o pipefail

toolchain=$(realpath $(dirname $AR)/..)
arch=$(echo $HOST | sed 's/-.*//; s/i686/i386/')

ndk_version=$("$RECIPE_DIR/version.sh")
if [ "$ndk_version" != "$PKG_VERSION" ]; then
    echo "Version '$ndk_version' from NDK doesn't match version '$PKG_VERSION' from meta.yaml"
    exit 1
fi

mkdir -p $PREFIX/lib
cp $toolchain/lib/clang/$PKG_VERSION/lib/linux/$arch/libomp.so $PREFIX/lib
