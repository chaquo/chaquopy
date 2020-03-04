#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
toolchain=$(realpath ${1:?})

cd $target_dir
. build-common.sh
. build-common-tools.sh

build_dir="/tmp/openssl-build-$$"
rm -rf $build_dir
mkdir -p $build_dir
cd $build_dir

if [[ $(basename $toolchain) =~ '64' ]]; then
    bits="64"
else
    bits="32"
fi
$target_dir/openssl/Configure linux-generic$bits shared
make -j $(nproc)

install_dir="/tmp/openssl-install-$$"
rm -rf $install_dir
make install_sw DESTDIR=$install_dir
tmp_prefix="$install_dir/usr/local"
prefix="$sysroot/usr"
rm -rf $prefix/include/openssl
cp -af $tmp_prefix/include/* $prefix/include
rm -rf $prefix/lib/lib{crypto,ssl}*.so*
cp -af $tmp_prefix/lib/*.so* $prefix/lib
rm -r $install_dir

rm -r $build_dir

# Some library SONAMEs have a version number after the .so. Unfortunately the Android Gradle
# plugin will only package libraries whose names end with ".so", so we have to rename them.
#
# We also add a _chaquopy suffix in case libraries of the same name are already present in
# /system/lib. And we update the SONAME to match, so that anything compiled against the library
# will store the modified name. This is necessary on API 22 and older, where the dynamic linker
# ignores the SONAME attribute and uses the filename instead.
cd $sysroot/usr/lib
for name in crypto ssl; do
    old_name=$(readlink lib$name.so)
    new_name="lib${name}_chaquopy.so"
    if [ "$name" = "crypto" ]; then
        crypto_old_name=$old_name
        crypto_new_name=$new_name
    fi

    mv "$old_name" "$new_name"
    ln -s "$new_name" "$old_name"
    patchelf --set-soname "$new_name" "$new_name"
    if [ "$name" = "ssl" ]; then
        patchelf --replace-needed "$crypto_old_name" "$crypto_new_name" "$new_name"
    fi
done
