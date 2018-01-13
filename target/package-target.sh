#/bin/bash
set -eu

crystax=~/crystax-ndk-10.3.2
ndk="$ANDROID_HOME/ndk-bundle"

short_ver="$1"      # e.g. "2.7"
minor_build="$2"    # e.g. "10-2" (see Common.java)
full_ver="$short_ver.$minor_build"
target_dir="$(pwd)"

for abi in armeabi-v7a x86; do
    echo "$abi"
    zipfile="$target_dir/target-$full_ver-$abi.zip"
    rm -f $zipfile
    rm -rf tmp
    mkdir tmp
    cd tmp

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

    zip -q -r "$zipfile" *
    cd ..
    rm -r tmp
done

echo "stdlib"
cp "$crystax/sources/python/$short_ver/libs/x86/stdlib.zip" "$target_dir/target-$full_ver-stdlib.zip"
