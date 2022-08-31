#!/bin/bash
set -eu -o pipefail
shopt -s inherit_errexit

recipe_dir=$(dirname $(realpath $0))
version_short=${1:?}

cd $recipe_dir/..

common_java="../product/buildSrc/src/main/java/com/chaquo/python/Common.java"
common_line=$(grep "PYTHON_VERSIONS.put(\"$version_short" $common_java)
read micro build < \
     <(echo $common_line | sed -E "s/.*\"$version_short.([0-9]+)\", \"([0-9]+)\".*/\1 \2/")
version=$version_short.$micro

./for-each-abi.sh python/build.sh $version
./package-target.sh toolchains ../maven/com/chaquo/python/target/$version-$build
