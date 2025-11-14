#!/bin/bash
set -eu

# Positional arguments:
#  * Maven directory to unpack from, e.g. /path/to/com/chaquo/python/target/3.10.6-3.
#  * `prefix` directory to unpack into.

mkdir -p "${1:?}"
target_dir=$(cd ${1:?} && pwd)
prefix_dir=$(cd ${2:?} && pwd)

version=$(basename "$target_dir")
version_short=$(echo $version | sed -E 's/^([0-9]+\.[0-9]+).*/\1/')

tmp_dir="/tmp/unpackage-target-$$"
mkdir "$tmp_dir"

for zip_path in $target_dir/*.zip; do
    zip_basename=$(basename $zip_path)
    abi_regex="^target-$version-(.+).zip$"
    if ! echo "$zip_basename" | grep -qE "$abi_regex"; then
        echo "$zip_path does not match $abi_regex"
        exit 1
    fi
    abi=$(echo "$zip_basename" | sed -E "s/$abi_regex/\1/")
    if echo $abi | grep -q stdlib; then continue; fi

    echo "$abi"
    abi_dir="$tmp_dir/$abi"
    mkdir "$abi_dir"
    unzip -q -d "$abi_dir" "$target_dir/target-$version-$abi.zip"

    prefix="$prefix_dir/$abi"
    mkdir -p "$prefix/include"
    cp -a "$abi_dir/include/"* "$prefix/include"

    mkdir -p "$prefix/lib"
    cp -a "$abi_dir/jniLibs/$abi/"* "$prefix/lib"
    for name in "$prefix/lib/"*_chaquopy.so; do
        ln -sf "$(basename "$name")" "$(echo $name | sed 's/_chaquopy//')"
    done

    # TODO: this gives every ABI the _sysconfigdata module from x86_64. This causes problems
    # with Rust packages such as tokenizers, which access that module at build time
    # (https://github.com/PyO3/pyo3/blob/v0.12.4/build.rs).
    lib_python="$prefix/lib/python$version_short"
    rm -rf "$lib_python"
    mkdir -p "$lib_python"
    unzip -q -d "$lib_python" "$target_dir/target-$version-stdlib.zip"
done

rm -rf "$tmp_dir"
