#!/bin/bash
set -eu

build_dir=$1
mkdir -p $build_dir
cd $build_dir

unset AR ARFLAGS AS CC CFLAGS CPP CPPFLAGS CXX CXXFLAGS F77 F90 FARCH FC LD LDFLAGS LDSHARED \
      NM RANLIB READELF STRIP

cmake -G Ninja ..
cmake --build . --target llvm-tblgen -- -j $(nproc)
