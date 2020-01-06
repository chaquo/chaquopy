#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
script=$(realpath ${1:?})

for toolchain in $target_dir/toolchains/*; do
    $script $toolchain
done
