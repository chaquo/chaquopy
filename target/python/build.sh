#!/bin/bash
set -eu -o pipefail

recipe_dir=$(dirname $(realpath $0))
PREFIX=$(realpath ${1:?})
version=${2:?}
read version_major version_minor < <(echo $version | sed -E 's/^([0-9]+)\.([0-9]+).*/\1 \2/')
version_short=$version_major.$version_minor
version_int=$(($version_major * 100 + $version_minor))

abi=$(basename $PREFIX)
cd $recipe_dir
. ../abi-to-host.sh
. ../android-env.sh

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

patches="soname"
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

# For a given Python version, we can't change the OpenSSL major version after we've
# made the first release, because that would break binary compatibility with our
# existing builds of the `cryptography` package.
libs="bzip2-1.0.8-2 libffi-3.4.4-3 sqlite-3.45.3-0 xz-5.4.6-1"
if [ $version_int -le 38 ]; then
    libs+=" openssl-1.1.1w-0"
else
    libs+=" openssl-3.0.15-1"
fi

url_prefix="https://github.com/beeware/cpython-android-source-deps/releases/download"
for name_ver in $libs; do
    url="$url_prefix/$name_ver/$name_ver-$HOST.tar.gz"
    echo "$url"
    curl -Lf "$url" | tar -x -C $PREFIX
done

# Add sysroot paths, otherwise Python 3.8's setup.py will think libz is unavailable.
CFLAGS+=" -I$toolchain/sysroot/usr/include"
LDFLAGS+=" -L$toolchain/sysroot/usr/lib/$HOST/$api_level"

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

configure_args="--host=$HOST --build=$(./config.guess) \
--enable-shared --without-ensurepip --with-openssl=$PREFIX"

# This prevents the "getaddrinfo bug" test, which can't be run when cross-compiling.
configure_args+=" --enable-ipv6"

if [ $version_int -ge 311 ]; then
    configure_args+=" --with-build-python=yes"
fi

./configure $configure_args

make -j $CPU_COUNT
make install prefix=$PREFIX
