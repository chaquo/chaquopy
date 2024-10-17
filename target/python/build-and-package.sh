#!/bin/bash
set -eu -o pipefail

recipe_dir=$(cd $(dirname $0) && pwd)
version_short=${1:?}

cd $recipe_dir/..

version_micro=$(./list-versions.py --micro | grep "^$version_short\." || true)
version_build=$(./list-versions.py --build | grep "^$version_short\." || true)

if [ -z "$version_micro" ] || [ -z "$version_build" ]; then
    echo "Invalid version '$version_short'" >&2
    exit 1
fi

case $version_short in
    3.8|3.9|3.10|3.11)
        abis="armeabi-v7a arm64-v8a x86 x86_64"
        ;;
    *)
        abis="arm64-v8a x86_64"
        ;;
esac

for abi in $abis; do
    python/build.sh prefix/$abi $version_micro
done

cd prefix
../package-target.sh ../../maven/com/chaquo/python/target/$version_build $abis
