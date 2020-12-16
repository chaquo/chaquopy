#!/bin/bash
#
# Positional arguments:
#  * Python major.minor version, e.g. "3.8"
#  * Python micro version and build number, separated by a dash, e.g. "1-2" (see Common.java)
#  * Maven target directory, e.g. /path/to/com/chaquo/python/target

set -eu

this_dir=$(dirname $(realpath $0))

short_ver="${1:?}"
micro_build="${2:?}"
full_ver="$short_ver.$micro_build"

mkdir -p "${3:?}"
target_dir="$(realpath $3)/$full_ver"
mkdir "$target_dir"  # Fail if it already exists: we don't want to overwrite things by accident.
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
</project>
EOF

tmp_dir="$target_dir/tmp"
rm -rf "$tmp_dir"
mkdir "$tmp_dir"
cd "$tmp_dir"

for toolchain_dir in $this_dir/toolchains/*; do
    abi=$(basename $toolchain_dir)
    echo "$abi"
    mkdir "$abi"
    cd "$abi"
    prefix="$toolchain_dir/sysroot/usr"

    mkdir include
    cp -a "$prefix/include/"{python$short_ver*,openssl,sqlite*} include

    jniLibs_dir="jniLibs/$abi"
    mkdir -p "$jniLibs_dir"
    cp "$prefix/lib/libpython$short_ver"*.so "$jniLibs_dir"
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

    # x86_64 strip segfaults on every file.
    if [ $abi = "x86_64" ]; then
        STRIP="strip"
    else
        STRIP=$toolchain_dir/*/bin/strip
    fi
    chmod u+w $(find -name *.so)
    $STRIP $(find -name *.so)

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
rm -r curses dbm idlelib tkinter turtle*

# Remove things which are large and unnecessary.
rm -r ensurepip pydoc_data
find -name test -or -name tests | xargs rm -r

# The build generates these files with the version number of the build Python, not the target
# Python. The source .txt files can't be used instead, because lib2to3 can only load them from
# real files, not via zipimport.
micro=$(echo $micro_build | sed 's/-.*//')
for src_filename in lib2to3/*.pickle; do
    tgt_filename=$(echo $src_filename | sed -E "s/$short_ver\\.[0-9]+/$short_ver.$micro/")
    if [[ $src_filename != $tgt_filename ]]; then
        mv $src_filename $tgt_filename
    fi
done

stdlib_zip="$target_prefix-stdlib.zip"
rm -f $stdlib_zip
zip -q -i '*.py' '*.pickle' -r $stdlib_zip .

echo "stdlib-pyc"
# zipimport doesn't support __pycache__ directories,
find -name __pycache__ | xargs rm -r

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
