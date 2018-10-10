#!/bin/bash
set -eu

mkdir -p maven

echo "# gradle"
gradle_dir=maven/com/chaquo/python/gradle/$(cat VERSION.txt)
mkdir -p $gradle_dir
cp product/gradle-plugin/build/libs/* $gradle_dir

echo "# target"
target_dir=maven/com/chaquo/python/target
common_java="product/buildSrc/src/main/java/com/chaquo/python/Common.java"
for major_minor in 2.7 3.6; do
    echo "## $major_minor"
    line=$(grep "PYTHON_BUILD_NUMBERS.put(\"$major_minor" $common_java | tail -n1)
    micro=$(echo $line | sed -E "s/.*\"$major_minor.([0-9]+).*/\1/")
    build=$(echo $line | sed -E "s/.*, \"([0-9]+).*/\1/")
    ./target/package-target.sh crystax $major_minor $micro-$build $target_dir
done
