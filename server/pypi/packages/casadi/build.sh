#!/bin/bash
set -eu

for flag in $CFLAGS; do
    if echo $flag | grep -q "^-I.*sources/python"; then
        python_include_dir=$(echo $flag | sed 's/^..//')
    fi
done

for flag in $LDFLAGS; do
    if echo $flag | grep -q "^-L.*sources/python"; then
        python_lib_dir=$(echo $flag | sed 's/^..//')
    elif echo $flag | grep -q "^-lpython"; then
        python_lib=$(echo $flag | sed 's/^..//')
    fi
done

# WITH_DEEPBIND=OFF because RTLD_DEEPBIND is not defined on Android.
cmake -DCMAKE_TOOLCHAIN_FILE=../chaquopy.toolchain.cmake \
      -DCMAKE_INSTALL_PREFIX=$PREFIX -DPYTHON_PREFIX=$PREFIX/.. \
      -DWITH_PYTHON=ON -DWITH_PYTHON3=ON \
      -DPYTHON_INCLUDE_DIR=$python_include_dir \
      -DPYTHON_LIBRARY=$python_lib_dir/lib$python_lib.so \
      -DWITH_DEEPBIND=OFF

make -j $CPU_COUNT
make install
