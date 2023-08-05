#!/bin/bash
set -eu -o pipefail

recipe_dir=$(cd $(dirname $0) && pwd)
version_short=${1:?}

cd $recipe_dir/..

version_micro=$(./list-versions.py --micro | grep "^$version_short\.")
version_build=$(./list-versions.py --build | grep "^$version_short\.")

./for-each-abi.sh python/build.sh $version_micro
./package-target.sh prefix ../maven/com/chaquo/python/target/$version_build
