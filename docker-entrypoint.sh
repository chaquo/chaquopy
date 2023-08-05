#!/bin/bash
set -eu

target_dir=maven/com/chaquo/python/target
common_java="product/buildSrc/src/main/java/com/chaquo/python/internal/Common.java"
extract_string='s/.*"(.*)".*/\1/'
python_version=$(grep "PYTHON_VERSION =" $common_java | sed -E "$extract_string")
build=$(grep "PYTHON_BUILD_NUM =" $common_java | sed -E "$extract_string")
major_minor=$(echo $python_version | sed -E 's/(.*)\..*/\1/')
micro=$(echo $python_version | sed -E 's/.*\.(.*)/\1/')
./target/package-target.sh $major_minor $micro-$build $target_dir
