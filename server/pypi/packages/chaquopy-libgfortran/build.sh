#!/bin/bash
set -eu

toolchain=$(realpath $(dirname $FC)/..)

toolchain_version=$($FC --version | head -n1 | sed -E 's/^GNU Fortran \(.*\) ([0-9](\.[0-9])+).*/\1/')
if [[ $toolchain_version != $PKG_VERSION ]]; then
    echo "Toolchain version '$toolchain_version' doesn't match meta.yaml version '$PKG_VERSION'"
    exit 1
fi

mkdir -p $PREFIX/lib
cp $(dirname $CC)/../*/lib*/libgfortran.so.3 $PREFIX/lib
