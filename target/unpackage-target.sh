#!/bin/bash
set -eu

# Positional arguments:
#  * `prefix` directory to unpack into. Must already contain ABI subdirectories, but can
#    otherwise be empty.
#  * Maven directory to unpack from, e.g. /path/to/com/chaquo/python/target/3.10.6-3.

prefix_dir=$(realpath ${1:?})
target_dir=$(realpath -m ${2:?})

version=$(basename "$target_dir")
version_short=$(echo $version | sed -E 's/^([0-9]+\.[0-9]+).*/\1/')

tmp_dir="/tmp/unpackage-target-$$"
mkdir "$tmp_dir"

cd "$prefix_dir"
for abi in *; do
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
