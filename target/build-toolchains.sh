#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
ndk=$(realpath ${1:?})
abis=${2:?}

for abi in $abis; do
    echo $abi
    if [[ $abi =~ "64" ]]; then api=21; else api=16; fi
    "$target_dir/build-toolchain.sh" $ndk $abi $api
done
