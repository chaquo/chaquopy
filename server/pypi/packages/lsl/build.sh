#!/bin/bash
set -eu

mkdir build
cd build

# LSL_OPTIMIZATIONS enables CMAKE_INTERPROCEDURAL_OPTIMIZATION, which in CMake 3.18.4
# (/usr/share/cmake-3.18/Modules/Compiler/Clang.cmake) adds -fuse-ld=gold to the linker
# command line, which causes "unknown option" errors.
cmake .. -DCMAKE_TOOLCHAIN_FILE="$SRC_DIR/../chaquopy.toolchain.cmake" \
      -DCMAKE_INSTALL_PREFIX="$PREFIX" \
      -DLSL_OPTIMIZATIONS=OFF

cmake --build . -j $CPU_COUNT
cmake --build . --target install