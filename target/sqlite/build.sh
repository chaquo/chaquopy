#!/bin/bash
set -eu

recipe_dir=$(dirname $(realpath $0))
prefix=$(realpath ${1:?})

# We pass in the version in the same format as the URL. For example, version 3.39.2
# becomes 3390200.
year=${2:?}
version=${3:?}

cd $recipe_dir
. ../build-common.sh

version_dir=$recipe_dir/build/$version
mkdir -p $version_dir
cd $version_dir
src_filename=sqlite-autoconf-$version.tar.gz
wget -c https://www.sqlite.org/$year/$src_filename

build_dir=$version_dir/$abi
rm -rf $build_dir
mkdir $build_dir
cd $build_dir
tar -xf $version_dir/$src_filename
cd $(basename $src_filename .tar.gz)

CFLAGS+=" -Os"  # This is off by default, but it's recommended in the README.
./configure --host=$host_triplet --disable-static --disable-static-shell --with-pic
make -j $(nproc)
make install prefix=$prefix

# We add a _chaquopy suffix in case libraries of the same name are provided by Android
# itself. And we update the SONAME to match, so that anything compiled against the library
# will store the modified name. This is necessary on API 22 and older, where the dynamic
# linker ignores the SONAME attribute and uses the filename instead.
cd $prefix/lib
for name in sqlite3; do
    old_name=$(basename $(realpath lib$name.so))  # Follow symlinks.
    new_name="lib${name}_chaquopy.so"
    mv "$old_name" "$new_name"
    ln -s "$new_name" "$old_name"
    patchelf --set-soname "$new_name" "$new_name"
done
