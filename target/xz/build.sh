#!/bin/bash
set -eu

recipe_dir=$(dirname $(realpath $0))
prefix=$(realpath ${1:?})
version=${2:?}

cd $recipe_dir
. ../build-common.sh

# Official packages are on SourceForge, which, within Docker, returned an endless series
# of redirections between mirrors. So use GitHub instead.
version_dir=$recipe_dir/build/$version
mkdir -p $version_dir
cd $version_dir
src_filename=v$version.tar.gz
wget -c https://github.com/xz-mirror/xz/archive/refs/tags/$src_filename

build_dir=$version_dir/$abi
rm -rf $build_dir
mkdir $build_dir
cd $build_dir
tar -xf $version_dir/$src_filename
cd xz-$version

./autogen.sh
./configure --host=$host_triplet --prefix=$prefix --disable-shared --with-pic
make -j $(nproc)
make install
