#!/bin/bash
set -eu

git clone --depth=1 https://github.com/sccn/liblsl.git
cmake .. -DCMAKE_TOOLCHAIN_FILE="$SRC_DIR/../chaquopy.toolchain.cmake" \
      -DCMAKE_INSTALL_PREFIX="$PREFIX" \
      -DBUILD_TESTING=OFF
cmake --build . -j $CPU_COUNT
cmake --build . --target install
