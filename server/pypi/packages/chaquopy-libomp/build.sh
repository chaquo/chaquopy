#!/bin/bash
set -eu

toolchain=$(realpath $(dirname $CC)/..)
arch=$(echo $CHAQUOPY_TRIPLET | sed 's/-.*//; s/i686/i386/')

mkdir -p $PREFIX/lib
cp $toolchain/lib64/clang/$PKG_VERSION/lib/linux/$arch/libomp.so $PREFIX/lib
