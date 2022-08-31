#!/bin/bash
set -eu

recipe_dir=$(dirname $(realpath $0))
toolchain=$(realpath ${1:?})
version=${2:?}

cd $recipe_dir
. ../build-common.sh
. ../build-common-tools.sh

version_dir=$recipe_dir/build/$version
mkdir -p $version_dir
cd $version_dir
src_filename=libffi-$version.tar.gz
wget -c ftp://sourceware.org/pub/libffi/libffi-$version.tar.gz

build_dir=$version_dir/$(basename $toolchain)
rm -rf $build_dir
mkdir $build_dir
cd $build_dir
tar -xf $version_dir/$src_filename
cd $(basename $src_filename .tar.gz)

./configure --host=$host_triplet --prefix=$sysroot/usr --disable-shared --with-pic
make -j $(nproc)
make install
