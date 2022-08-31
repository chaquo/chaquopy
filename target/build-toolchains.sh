#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))

for abi in armeabi-v7a arm64-v8a x86 x86_64; do
    echo $abi
    "$target_dir/build-toolchain.sh" $abi
done
