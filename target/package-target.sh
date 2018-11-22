#/bin/bash
#
# Positional arguments:
#  * Python major.minor version, e.g. "2.7"
#  * Python micro-build version, e.g. "14-2" (see Common.java)
#  * Target directory, e.g. /path/to/maven/com/chaquo/python/target

set -eu

this_dir=$(dirname $(realpath $0))

short_ver="${1:?}"
micro_build="${2:?}"
full_ver="$short_ver.$micro_build"

target_parent="$(realpath ${3:?})"
target_dir="$target_parent/$full_ver"
mkdir -p "$target_dir"
target_prefix="$target_dir/target-$full_ver"

tmp_dir="$target_dir/tmp"
rm -rf "$tmp_dir"
mkdir "$tmp_dir"
cd "$tmp_dir"

for toolchain_dir in $this_dir/toolchains/*; do
    abi=$(basename $toolchain_dir)
    echo "$abi"
    mkdir "$abi"
    cd "$abi"

    gcc_abi=$abi
    if [[ $abi == "arm64-v8a" ]]; then
        gcc_abi="aarch64"
    elif [[ $abi == "armeabi"* ]]; then
        gcc_abi="arm"
    fi
    prefix="$toolchain_dir/sysroot/usr"

    jniLibs_dir="jniLibs/$abi"
    mkdir -p "$jniLibs_dir"
    cp "$prefix/lib/libpython$short_ver"*.so "$jniLibs_dir"

    # TODO
    if false; then
        cp "$crystax/sources/sqlite/3/libs/$abi/libsqlite3.so" "$jniLibs_dir"

        for openssl_lib in crypto ssl; do
            src_filename=$(echo $crystax/sources/openssl/*/libs/$abi/lib${openssl_lib}.so)
            if [ $(echo "$src_filename" | wc -w) != "1" ]; then
                echo "Found multiple versions of OpenSSL in Crystax NDK: delete the ones you don't want to use"
                exit 1
            fi
            # build-target-openssl.sh changes the SONAMEs to avoid clashing with the system copies.
            # This isn't necessary for SQLite because the system copy is just "libsqlite.so", with
            # no "3".
            cp "$src_filename" "$jniLibs_dir/lib${openssl_lib}_chaquopy.so"
        done
    fi

    mkdir lib-dynload
    dynload_dir="lib-dynload/$abi"
    mkdir -p $dynload_dir
    for module in $prefix/lib/python$short_ver/lib-dynload/*; do
        cp $module $dynload_dir/$(basename $module | sed 's/.cpython-.*.so/.so/')
    done
    rm $dynload_dir/_test*.so

    chmod u+w $(find -name *.so)
    $toolchain_dir/$gcc_abi-*/bin/strip $(find -name *.so)

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
for filename in lib2to3/*.pickle; do
    mv $filename $(echo $filename | sed "s/$short_ver.[0-9]/$short_ver.$micro/")
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
