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

build_dir="/tmp/python-build-$$"
rm -rf $build_dir
mkdir -p $build_dir
cd $build_dir

# Override some tests.
cat > config.site <<EOF
# Prevent "-dirty" appearing in console banner when building from modified source.
ac_cv_prog_HAS_GIT=no

# Things that can't be autodetected when cross-compiling.
ac_cv_aligned_required=no  # Default of "yes" changes hash function to FNV, which breaks Numba.
ac_cv_file__dev_ptmx=no
ac_cv_file__dev_ptc=no

# Broken before API level 21 (see build-toolchain.sh), but because configure does a link test
# rather than a header test, it would still detect it.
ac_cv_func_wcsftime=no
EOF
export CONFIG_SITE=$(pwd)/config.site

# --enable-ipv6 prevents the "getaddrinfo bug" test, which can't be run when cross-compiling.
$target_dir/python/configure --host=$host_triplet --build=x86_64-linux-gnu \
    --enable-shared --enable-ipv6 --without-ensurepip --with-openssl=$sysroot/usr

make -j $(nproc)
make install prefix=$sysroot/usr

rm -r $build_dir

# Some library SONAMEs have a version number after the .so. Unfortunately the Android Gradle
# plugin will only package libraries whose names end with ".so", so we have to rename them. And
# we update the SONAME to match, so that anything compiled against the library will store the
# modified name. This is necessary on API 22 and older, where the dynamic linker ignores the
# SONAME attribute and uses the filename instead.
cd $sysroot/usr/lib
new_name=$(echo libpython*.*.so)
old_name=$(readlink $new_name)
patchelf --set-soname "$new_name" "$new_name"
for module in python*/lib-dynload/*; do
    patchelf --replace-needed "$old_name" "$new_name" "$module"
done
