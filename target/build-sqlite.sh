#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
toolchain=$(realpath ${1:?})

cd $target_dir
. build-common.sh
. build-common-tools.sh

cd sqlite

# SQLite hasn't updated their version of autoconf since 2008, so it doesn't know about Android
# or ARM64 (http://sqlite.1065341.n5.nabble.com/Feature-request-Support-for-aarch64-td68361.html).
cp ../python/config.sub .

# Create minimal fossil manifest and manifest.uuid files (see https://repo.or.cz/w/sqlite.git).
hash="0000000000000000000000000000000000000000"
echo $hash > manifest.uuid
cat >manifest <<EOF
C $hash
D $(date +%Y-%m-%dT%H:%M:%S)
EOF

build_dir="/tmp/sqlite-build-$$"
rm -rf $build_dir
mkdir -p $build_dir
cd $build_dir

$target_dir/sqlite/configure --host=$host_triplet
make -j $(nproc)
make install prefix=$sysroot/usr

rm -r $build_dir

# Some library SONAMEs have a version number after the .so. Unfortunately the Android Gradle
# plugin will only package libraries whose names end with ".so", so we have to rename them.
#
# We also add a _chaquopy suffix in case libraries of the same name are already present in
# /system/lib. And we update the SONAME to match, so that anything compiled against the library
# will store the modified name. This is necessary on API 22 and older, where the dynamic linker
# ignores the SONAME attribute and uses the filename instead.
cd $sysroot/usr/lib
for name in sqlite3; do
    old_name=$(readlink lib$name.so)
    new_name="lib${name}_chaquopy.so"
    mv "$old_name" "$new_name"
    ln -s "$new_name" "$old_name"
    patchelf --set-soname "$new_name" "$new_name"
done
