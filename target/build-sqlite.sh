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
