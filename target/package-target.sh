#/bin/bash
set -eu

crystax=~/crystax-ndk-10.3.2
ndk="$ANDROID_HOME/ndk-bundle"

short_ver="${1:?}"      # e.g. "2.7"
minor_build="${2:?}"    # e.g. "10-2" (see Common.java)
full_ver="$short_ver.$minor_build"
target_dir="$(cd ${3:?}; pwd)"
target_prefix="$target_dir/target-$full_ver"

tmp_dir="/tmp/package-target-$$"
mkdir "$tmp_dir"
cd "$tmp_dir"

for abi in armeabi-v7a x86; do
    echo "$abi"
    mkdir "$abi"
    cd "$abi"

    jniLibs_dir="jniLibs/$abi"
    mkdir -p "$jniLibs_dir"
    cp -a "$crystax/sources/python/$short_ver/libs/$abi/libpython${short_ver}"*.so "$jniLibs_dir"
    cp -a "$crystax/sources/crystax/libs/$abi/libcrystax.so" "$jniLibs_dir"

    mkdir lib-dynload
    dynload_dir="lib-dynload/$abi"
    cp -a "$crystax/sources/python/$short_ver/libs/$abi/modules" "$dynload_dir"

    if [[ $abi == "arm64-v8a" ]]; then
        gcc_abi="aarch64"
    elif [[ $abi == "armeabi"* ]]; then
        gcc_abi="arm"
    else
        gcc_abi=$abi
    fi
    $ndk/toolchains/$gcc_abi-*/prebuilt/*/*/bin/strip $(find -name *.so)

    abi_zip="$target_prefix-$abi.zip"
    rm -f "$abi_zip"
    zip -q -r "$abi_zip" .
    cd ..
done

echo "stdlib"
stdlib_zip="$target_prefix-stdlib.zip"
cp "$crystax/sources/python/$short_ver/libs/x86/stdlib.zip" "$stdlib_zip"

echo "stdlib-pyc"
mkdir stdlib
# Run compileall from the parent directory: that way the "stdlib/" prefix gets encoded into the
# .pyc files and will appear in traceback messages.
unzip -q "$stdlib_zip" -d stdlib
compileall_args=""
if echo "$short_ver" | grep -q "^3"; then
    compileall_args="-b"  # zipimport doesn't support __pycache__ directories.
fi
"python$short_ver" -m compileall -q "$compileall_args" stdlib

stdlib_pyc_zip="$target_prefix-stdlib-pyc.zip"
rm -f "$stdlib_pyc_zip"
cd stdlib
zip -q -i '*.pyc' -r "$stdlib_pyc_zip" .
cd ..

rm -rf "$tmp_dir"
