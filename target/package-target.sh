#/bin/bash
set -eu

script_dir="$(dirname "$0")"
start_dir="$(pwd)"

crystax=~/crystax-ndk-10.3.2
ndk=~/android-ndk-r14b

short_ver=2.7
full_ver=2.7.10-2  # See "build number" in PythonPlugin.groovy
target_dir="$start_dir/com/chaquo/python/target/$full_ver"
rm -rf "$target_dir"
mkdir -p "$target_dir"

for abi in armeabi-v7a x86; do
    echo "$abi"
    zipfile="$target_dir/target-$full_ver-$abi.zip"
    rm -f $zipfile
    rm -rf tmp
    mkdir tmp
    cd tmp

    jniLibs_dir="jniLibs/$abi"
    mkdir -p "$jniLibs_dir"
    cp -a "$crystax/sources/python/$short_ver/libs/$abi/libpython$short_ver.so" "$jniLibs_dir"
    cp -a "$crystax/sources/crystax/libs/$abi/libcrystax.so" "$jniLibs_dir"

    mkdir lib-dynload
    dynload_dir="lib-dynload/$abi"
    cp -a "$crystax/sources/python/$short_ver/libs/$abi/modules" "$dynload_dir"
    rm "$dynload_dir/_sqlite3.so"  # TODO 5160

    if [[ $abi == "arm64-v8a" ]]; then
        gcc_abi="aarch64"
    elif [[ $abi == "armeabi"* ]]; then
        gcc_abi="arm"
    else
        gcc_abi=$abi
    fi
    $ndk/toolchains/$gcc_abi-*/prebuilt/*/*/bin/strip $(find -name *.so)

    zip -q -r "$zipfile" *
    cd ..
    rm -r tmp
done

echo "stdlib"
cp "$crystax/sources/python/$short_ver/libs/x86/stdlib.zip" "$target_dir/target-$full_ver-stdlib.zip"

"$script_dir/update_checksums.sh" "$start_dir/com"
