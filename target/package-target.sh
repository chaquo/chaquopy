#/bin/bash
#
# Positional arguments:
#  * Path to Crystax NDK
#  * Python major.minor version, e.g. "2.7"
#  * Python micro-build version, e.g. "14-2" (see Common.java)
#  * Target directory, e.g. /var/www/chaquo/maven/com/chaquo/python/target

set -eu

crystax="$(cd ${1:?} && pwd)"
short_ver="${2:?}"
micro_build="${3:?}"
full_ver="$short_ver.$micro_build"

crystax_python_dir="$crystax/sources/python/$short_ver"

mkdir -p "${4:?}"
target_dir="$(cd $4 && pwd)/$full_ver"
mkdir "$target_dir"  # Error if already exists: don't want to overwrite existing files.
target_prefix="$target_dir/target-$full_ver"

tmp_dir="$target_dir/tmp"
mkdir "$tmp_dir"
cd "$tmp_dir"

for abi in armeabi-v7a arm64-v8a x86 x86_64; do
    echo "$abi"
    mkdir "$abi"
    cd "$abi"

    cp -a "$crystax_python_dir/include" .

    gcc_abi=$abi
    libcrystax_abi=$abi
    if [[ $abi == "arm64-v8a" ]]; then
        gcc_abi="aarch64"
    elif [[ $abi == "armeabi"* ]]; then
        gcc_abi="arm"
        libcrystax_abi="armeabi-v7a/thumb"
    fi

    jniLibs_dir="jniLibs/$abi"
    mkdir -p "$jniLibs_dir"
    cp "$crystax_python_dir/libs/$abi/libpython${short_ver}"*.so "$jniLibs_dir"
    cp "$crystax/sources/crystax/libs/$libcrystax_abi/libcrystax.so" "$jniLibs_dir"
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

    mkdir lib-dynload
    dynload_dir="lib-dynload/$abi"
    cp -a "$crystax_python_dir/libs/$abi/modules" "$dynload_dir"

    chmod u+w $(find -name *.so)
    $crystax/toolchains/$gcc_abi-*4.9/prebuilt/*/*/bin/strip $(find -name *.so)

    abi_zip="$target_prefix-$abi.zip"
    rm -f "$abi_zip"
    zip -q -r "$abi_zip" .
    cd ..
done

echo "stdlib"
stdlib_zip="$target_prefix-stdlib.zip"
cp "$crystax_python_dir/libs/x86/stdlib.zip" "$stdlib_zip"

echo "stdlib-pyc"
mkdir stdlib
# Run compileall from the parent directory: that way the "stdlib/" prefix gets encoded into the
# .pyc files and will appear in traceback messages.
unzip -q "$stdlib_zip" -d stdlib
"python$short_ver" -m compileall -qb stdlib

stdlib_pyc_zip="$target_prefix-stdlib-pyc.zip"
rm -f "$stdlib_pyc_zip"
cd stdlib
zip -q -i '*.pyc' '*.pickle' -r "$stdlib_pyc_zip" .
cd ..

rm -rf "$tmp_dir"
