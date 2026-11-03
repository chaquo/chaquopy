#!/bin/bash

# Set up the build directory
mkdir -p build
cd build

cmake .. -DCMAKE_INSTALL_PREFIX=$CHAQUOPY_LIB/ctranslate2-lib \
         -DCMAKE_LIBRARY_PATH=/home/aryan/llvm-project/openmp/runtime/src/libiomp5.so

# Compile the C++ library
make -j4
sudo make install
sudo ldconfig
