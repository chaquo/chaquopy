#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
toolchain=$(realpath ${1:?})

cd $target_dir
. build-common.sh
. build-common-tools.sh

# This is redundant since --sysroot is already in the script pointed to by $CC, but
# python/setup.py needs it to know where to search for header and library files.
export CC="$CC --sysroot=$sysroot"

# The configure script omits -fPIC on Android, because it was unnecessary on older versions of
# the NDK (https://bugs.python.org/issue26851). But it's definitely necessary on the current
# version, otherwise we get linker errors like "Parser/myreadline.o: relocation R_386_GOTOFF
# against preemptible symbol PyOS_InputHook cannot be used when making a shared object".
export CCSHARED="-fPIC"

cd python

# Set some things which can't be autodetected when cross-compiling.
cat > config.site <<EOF
ac_cv_file__dev_ptmx=no
ac_cv_file__dev_ptc=no
ac_cv_func_gethostbyname_r=no
ac_cv_func_faccessat=no
EOF
export CONFIG_SITE=$(pwd)/config.site

build_dir="/tmp/python-build-$$"
rm -rf $build_dir
mkdir -p $build_dir
cd $build_dir

# --enable-ipv6 prevents the "getaddrinfo bug" test, which can't be run when cross-compiling.
$target_dir/python/configure --host=$host_triplet --build=x86_64-linux-gnu \
    --enable-shared --enable-ipv6 --without-ensurepip --with-openssl=$sysroot/usr
make -j $(nproc)
make install prefix=$sysroot/usr

rm -r $build_dir
