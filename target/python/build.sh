#!/bin/bash
set -eu -o pipefail

recipe_dir=$(dirname $(realpath $0))
PREFIX=${1:?}
mkdir -p "$PREFIX"
PREFIX=$(realpath "$PREFIX")

version=${2:?}
read version_major version_minor version_micro < <(
    echo $version | sed -E 's/^([0-9]+)\.([0-9]+)\.([0-9]+).*/\1 \2 \3/'
)
version_short=$version_major.$version_minor
version_no_pre=$version_major.$version_minor.$version_micro
version_int=$(($version_major * 100 + $version_minor))

abi=$(basename $PREFIX)
cd $recipe_dir
. ../abi-to-host.sh
. ../android-env.sh

# Download and unpack Python source code.
version_dir=$recipe_dir/build/$version
mkdir -p $version_dir
cd $version_dir
src_filename=Python-$version.tgz
wget -c https://www.python.org/ftp/python/$version_no_pre/$src_filename

build_dir=$version_dir/$abi
rm -rf $build_dir
tar -xf "$src_filename"
mv "Python-$version" "$build_dir"
cd "$build_dir"

# Apply patches.
patches=""
if [ $version_int -le 311 ]; then
    patches+=" sysroot_paths"
fi
if [ $version_int -eq 311 ]; then
    patches+=" python_for_build_deps"
fi
if [ $version_int -le 312 ]; then
    patches+=" soname"
fi
if [ $version_int -eq 312 ]; then
    patches+=" bldlibrary grp"
fi
if [ $version_int -eq 313 ]; then
    # TODO: remove this once it's merged upstream.
    patches+=" 3.13_pending"
fi
for name in $patches; do
    patch_file="$recipe_dir/patches/$name.patch"
    echo "$patch_file"
    patch -p1 -i "$patch_file"
done

# Remove any existing installation in the prefix.
rm -rf $PREFIX/{include,lib}/python$version_short
rm -rf $PREFIX/lib/libpython$version_short*

if [ $version_int -le 312 ]; then
    # Download and unpack libraries needed to compile Python. For a given Python
    # version, we must maintain binary compatibility with existing wheels.
    libs="bzip2-1.0.8-2 libffi-3.4.4-3 sqlite-3.45.3-3 xz-5.4.6-1"
    if [ $version_int -le 308 ]; then
        libs+=" openssl-1.1.1w-3"
    else
        libs+=" openssl-3.0.15-4"
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
    cd "$build_dir"
    cat > config.site <<-EOF
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

    # Some of the patches involve missing Makefile dependencies, which allowed extension
    # modules to be built before libpython3.x.so in parallel builds. In case this happens
    # again, make sure there's no libpython3.x.a, otherwise the modules may end up silently
    # linking with that instead.
    if [ $version_int -ge 310 ]; then
        configure_args+=" --without-static-libpython"
    fi

    if [ $version_int -ge 311 ]; then
        configure_args+=" --with-build-python=yes"
    fi

    ./configure $configure_args

    make -j $CPU_COUNT
    make install prefix=$PREFIX

# Python 3.13 and later comes with an official Android build script.
else
    mkdir -p cross-build/build
    ln -s "$(which python$version_short)" cross-build/build/python

    Android/android.py configure-host "$HOST"
    Android/android.py make-host "$HOST"
    cp -a "cross-build/$HOST/prefix/"* "$PREFIX"
fi
