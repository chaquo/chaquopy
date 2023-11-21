#!/bin/bash
set -eu -o pipefail

# Positional arguments:
#  * Maven directory to pack into, e.g. /path/to/com/chaquo/python/target/3.10.6-3. Must
#    not already exist.
#  * Multiple `prefix` subdirectories to pack from. Each must be named after an ABI.

this_dir=$(dirname $(realpath $0))
target_dir=${1:?}

prefixes=""
shift
if [ $# = "0" ]; then
    echo "Must provide at least one prefix subdirectory"
    exit 1
fi
while [ $# != "0" ]; do
    prefixes+=" $(realpath $1)"
    shift
done

mkdir -p $(dirname $target_dir)
mkdir "$target_dir"  # Fail if it already exists: we don't want to overwrite things by accident.
target_dir=$(realpath $target_dir)

full_ver=$(basename $target_dir)
short_ver=$(echo $full_ver | sed -E 's/^([0-9]+\.[0-9]+).*/\1/')
target_prefix="$target_dir/target-$full_ver"

cat > "$target_prefix.pom" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.chaquo.python</groupId>
    <artifactId>target</artifactId>
    <version>$full_ver</version>
    <packaging>pom</packaging>

    <name>Chaquopy</name>
    <description>The Python SDK for Android</description>
    <url>https://chaquo.com/chaquopy/</url>

    <licenses>
        <license>
            <name>MIT License</name>
            <url>https://opensource.org/licenses/MIT</url>
        </license>
    </licenses>

    <developers>
        <developer>
            <name>Malcolm Smith</name>
            <email>smith@chaquo.com</email>
        </developer>
    </developers>

    <scm>
        <connection>scm:git:https://github.com/chaquo/chaquopy.git</connection>
        <url>https://github.com/chaquo/chaquopy</url>
    </scm>
</project>
EOF

tmp_dir="$target_dir/tmp"
rm -rf "$tmp_dir"
mkdir "$tmp_dir"
cd "$tmp_dir"

for prefix in $prefixes; do
    unset abi api_level
    . "$this_dir/build-common.sh"
    echo "$abi"
    mkdir "$abi"
    cd "$abi"

    mkdir include
    cp -a "$prefix/include/"{python$short_ver,openssl,sqlite*} include

    jniLibs_dir="jniLibs/$abi"
    mkdir -p "$jniLibs_dir"
    cp $prefix/lib/libpython$short_ver.so "$jniLibs_dir"
    for name in crypto ssl sqlite3; do
        cp "$prefix/lib/lib${name}_chaquopy.so" "$jniLibs_dir"
    done

    mkdir lib-dynload
    dynload_dir="lib-dynload/$abi"
    mkdir -p $dynload_dir
    for module in $prefix/lib/python$short_ver/lib-dynload/*; do
        cp $module $dynload_dir/$(basename $module | sed 's/.cpython-.*.so/.so/')
    done
    rm $dynload_dir/*_test*.so

    chmod u+w $(find . -name *.so)
    $STRIP $(find . -name *.so)

    abi_zip="$target_prefix-$abi.zip"
    rm -f "$abi_zip"
    zip -q -r "$abi_zip" .
    cd ..
done

echo "stdlib"
cp -a $prefix/lib/python$short_ver stdlib
cd stdlib
rm -r lib-dynload site-packages

# Remove things which depend on missing native modules.
rm -r curses idlelib tkinter turtle*

# Remove things which are large and unnecessary.
rm -r ensurepip pydoc_data
find . -name test -or -name tests | xargs rm -r

# The build generates these files with the version number of the build Python, not the target
# Python. The source .txt files can't be used instead, because lib2to3 can only load them from
# real files, not via zipimport.
full_ver_no_build=$(echo $full_ver | sed 's/-.*//')
for src_filename in lib2to3/*.pickle; do
    tgt_filename=$(echo $src_filename |
                   sed -E "s/$short_ver.*\$/$full_ver_no_build.final.0.pickle/")
    if [[ $src_filename != $tgt_filename ]]; then
        mv $src_filename $tgt_filename
    fi
done

stdlib_zip="$target_prefix-stdlib.zip"
rm -f $stdlib_zip
zip -q -i '*.py' '*.pickle' -r $stdlib_zip .

echo "stdlib-pyc"
# zipimport doesn't support __pycache__ directories,
find . -name __pycache__ | xargs rm -r

# Run compileall from the parent directory: that way the "stdlib/" prefix gets encoded into the
# .pyc files and will appear in traceback messages.
cd ..
"python$short_ver" -m compileall -qb stdlib

stdlib_pyc_zip="$target_prefix-stdlib-pyc.zip"
rm -f "$stdlib_pyc_zip"
cd stdlib
zip -q -i '*.pyc' '*.pickle' -r "$stdlib_pyc_zip" .
cd ..

rm -rf "$tmp_dir"
