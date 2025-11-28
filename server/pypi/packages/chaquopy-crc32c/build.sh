#!/bin/bash
set -eu

mkdir -p build
cd build
rm -f CMakeCache.txt  # For rerunning with build-wheel.py --no-unpack.

cmake .. -DCRC32C_BUILD_TESTS=0 -DCRC32C_BUILD_BENCHMARKS=0 -DCRC32C_USE_GLOG=0 \
      -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=1 -DCMAKE_INSTALL_PREFIX="$PREFIX"

make -j $(nproc)
make install
