#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
script=$(realpath ${1:?})

shift
for prefix in $target_dir/prefix/*; do
    $script $prefix "$@"
done
