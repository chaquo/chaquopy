#!/bin/bash
#
# Positional arguments:
#  * Maven target version directory, e.g. /path/to/com/chaquo/python/target/3.6.5-11
#  * `toolchains` directory to unpack into: must already contain ABI subdirectories, but can
#     otherwise be empty.

set -eu

target_dir="$(realpath ${1:?})"
toolchains_dir="$(realpath "${2:?}")"

tmp_dir="/tmp/unpackage-target-$$"
mkdir "$tmp_dir"

cd "$toolchains_dir"
for abi in *; do
    abi_dir="$tmp_dir/$abi"
    mkdir "$abi_dir"
    unzip -q -d "$abi_dir" "$target_dir/target-"*"-$abi.zip"

    prefix="$toolchains_dir/$abi/sysroot/usr"
    mkdir -p "$prefix/include"
    cp -a "$abi_dir/include/"* "$prefix/include"

    mkdir -p "$prefix/lib"
    cp -a "$abi_dir/jniLibs/$abi/"* "$prefix/lib"
    for name in "$prefix/lib/"*_chaquopy.so; do
        ln -sf "$(basename "$name")" "$(echo $name | sed 's/_chaquopy//')"
    done
done

rm -rf "$tmp_dir"
