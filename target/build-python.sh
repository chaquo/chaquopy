#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
toolchain=$(realpath ${1:?})

cd $target_dir
. build-common.sh

# This is redundant since --sysroot is already in the script pointed to by $CC, but
# python/setup.py needs it to know where to search for header and library files.
export CC="$CC --sysroot=$sysroot"

cd python

# Set some things which can't be autodetected when cross-compiling.
cat > config.site <<EOF
ac_cv_file__dev_ptmx=no
ac_cv_file__dev_ptc=no
ac_cv_func_gethostbyname_r=no
ac_cv_func_faccessat=no
EOF
export CONFIG_SITE=$(pwd)/config.site

# --enable-ipv6 prevents the "getaddrinfo bug" test, which can't be run when cross-compiling.
./configure --host=$host_triplet --build=x86_64-linux-gnu \
            --enable-shared --enable-ipv6 --without-ensurepip
make -j $(nproc)
make install prefix=$sysroot/usr
