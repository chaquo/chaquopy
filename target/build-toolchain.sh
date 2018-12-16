#!/bin/bash
set -eu

target_dir=$(dirname $(realpath $0))
ndk=$(realpath ${1:?})
abi=${2:?}
api=${3:?}

if [ $abi == "armeabi-v7a" ]; then
    arch="arm"
elif [ $abi == "arm64-v8a" ]; then
    arch="arm64"
else
    arch=$abi
fi

toolchain="$target_dir/toolchains/$abi"
$ndk/build/tools/make_standalone_toolchain.py --arch $arch --api $api --install-dir $toolchain

# Standalone toolchains with unified headers rely on a command line argument in the Clang
# launcher scripts to define __ANDROID_API__. If it's not defined, which will be the case
# during the Fortran build, api-level.h assumes we're working on an unreleased Android version
# and sets it to 10000, which could cause all kinds of problems
# (https://android.googlesource.com/platform/ndk/+/ndk-r15-release/docs/UnifiedHeaders.md).
header="$toolchain/sysroot/usr/include/android/api-level.h"
pattern="#define __ANDROID_API__ __ANDROID_API_FUTURE__"
replacement="#define __ANDROID_API__ $api  /* Chaquopy: see build-toolchain.sh */"
grep -q "$pattern" $header
sed -i "s|$pattern|$replacement|" $header
