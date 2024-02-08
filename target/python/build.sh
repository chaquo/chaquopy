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

patches="dynload_shlib lfs soname"
if [ $version_int -le 311 ]; then
    patches+=" sysroot_paths"
fi
if [ $version_int -ge 311 ]; then
    # Although this patch applies cleanly to 3.12, it no longer has the intended effect,
    # because the stdlib extension modules are now built using autoconf rather than
    # distutils. Replace it with the fix we upstreamed to 3.13.
    patches+=" python_for_build_deps_REMOVED"
fi
if [ $version_int -ge 312 ]; then
    patches+=" bldlibrary grp"
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

configure_args="--host=$host_triplet --build=$(./config.guess) \
--enable-shared --without-ensurepip --with-openssl=$prefix"

# This prevents the "getaddrinfo bug" test, which can't be run when cross-compiling.
configure_args+=" --enable-ipv6"

if [ $version_int -ge 311 ]; then
    configure_args+=" --with-build-python=yes"
fi

./configure $configure_args

make -j $CPU_COUNT
make install prefix=$prefix
