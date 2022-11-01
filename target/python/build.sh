#!/bin/bash
set -eu

recipe_dir=$(dirname $(realpath $0))
prefix=$(realpath ${1:?})
version=${2:?}
read version_major version_minor < <(echo $version | sed -E 's/^([0-9]+)\.([0-9]+).*/\1 \2/')
version_short=$version_major.$version_minor
version_int=$(($version_major * 100 + $version_minor))

cd $recipe_dir
. ../build-common.sh

version_dir=$recipe_dir/build/$version
mkdir -p $version_dir
cd $version_dir
src_filename=Python-$version.tgz
wget -c https://www.python.org/ftp/python/$version/$src_filename

build_dir=$version_dir/$abi
rm -rf $build_dir
mkdir $build_dir
cd $build_dir
tar -xf $version_dir/$src_filename
cd $(basename $src_filename .tgz)

patches="dynload_shlib lfs sysroot_paths"
if [ $version_int -ge 311 ]; then
    patches+=" python_for_build_deps"
fi
for name in $patches; do
    patch -p1 -i $recipe_dir/patches/$name.patch
done

# Add sysroot paths, otherwise Python 3.8's setup.py will think libz is unavailable.
CFLAGS+=" -I$toolchain/sysroot/usr/include"
LDFLAGS+=" -L$toolchain/sysroot/usr/lib/$host_triplet/$api_level"

# The configure script omits -fPIC on Android, because it was unnecessary on older versions of
# the NDK (https://bugs.python.org/issue26851). But it's definitely necessary on the current
# version, otherwise we get linker errors like "Parser/myreadline.o: relocation R_386_GOTOFF
# against preemptible symbol PyOS_InputHook cannot be used when making a shared object".
export CCSHARED="-fPIC"

# Override some tests.
cat > config.site <<EOF
# Things that can't be autodetected when cross-compiling.
ac_cv_aligned_required=no  # Default of "yes" changes hash function to FNV, which breaks Numba.
ac_cv_file__dev_ptmx=no
ac_cv_file__dev_ptc=no
EOF
export CONFIG_SITE=$(pwd)/config.site

configure_args="--host=$host_triplet --build=x86_64-linux-gnu \
--enable-shared --without-ensurepip --with-openssl=$prefix"

# This prevents the "getaddrinfo bug" test, which can't be run when cross-compiling.
configure_args+=" --enable-ipv6"

if [[ $version =~ ^3\.11\. ]]; then
    configure_args+=" --with-build-python=yes"
fi

./configure $configure_args

make -j $(nproc)
make install prefix=$prefix

# We should now have a file named something like libpython3.8.so.1.0. But the Android
# Gradle plugin will only package libraries whose names end with ".so", so we rename it to
# simply libpython3.8.so. And we update the SONAME to match, so that anything compiled
# against the library will store the modified name. This is necessary on API 22 and older,
# where the dynamic linker ignores the SONAME attribute and uses the filename instead.
#
# If future Python versions ever start using ABI flags again (like "m" in Python 3.7), we
# will remove them here as well, to avoid dealing with them in the rest of the system.
cd $prefix/lib
new_name=libpython$version_short.so
old_name=$(basename $(realpath $new_name))  # Follow symlinks.
patchelf --set-soname "$new_name" "$new_name"
for module in python*/lib-dynload/*; do
    patchelf --replace-needed "$old_name" "$new_name" "$module"
done
