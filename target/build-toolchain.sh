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

cd "$target_dir"
toolchain=$(realpath -m "toolchains/$abi")
$ndk/build/tools/make_standalone_toolchain.py --arch $arch --api $api --install-dir $toolchain
. build-common.sh

# Standalone toolchains with unified headers rely on a command line argument in the Clang
# launcher scripts to define __ANDROID_API__. If it's not defined, which will be the case
# during the Fortran build, api-level.h assumes we're working on an unreleased Android version
# and sets it to 10000, which could cause all kinds of problems
# (https://android.googlesource.com/platform/ndk/+/ndk-r15-release/docs/UnifiedHeaders.md).
header="$sysroot/usr/include/android/api-level.h"
pattern="#define __ANDROID_API__ __ANDROID_API_FUTURE__"
replacement="#define __ANDROID_API__ $api  /* Chaquopy: see build-toolchain.sh */"
sed -i "s|$pattern|$replacement|" $header
grep -q "Chaquopy" "$header"

# localeconv isn't available until API level 21. setlocale is always available, but always
# fails before API 21. Add minimal implementations based on
# android/platform/bionic/libc/bionic/locale.cpp.
header="$sysroot/usr/include/locale.h"
sed -i.old 's|struct lconv\* localeconv(.*|/* Chaquopy localeconv: see build-toolchain.sh */ \
#include <limits.h> \
static struct lconv g_locale = { \
    ".", "", "", "", "", "", "", "", "", "", CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, \
    CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX \
}; \
static struct lconv* localeconv(void) { return \&g_locale; }|;

s|char\* setlocale(.*|/* Chaquopy setlocale: see build-toolchain.sh */ \
static char *setlocale(int category, const char *locale) { return "C.UTF-8"; } \
|' "$header"
grep -q "Chaquopy localeconv" "$header"
grep -q "Chaquopy setlocale" "$header"

# On Android, these libraries are incorporated into libc. Create empty .a files so we
# don't have to patch everything that links against them.
for name in pthread rt; do
    for ext in a so; do
        filename="$sysroot/usr/lib/lib$name.$ext"
        if [ -e "$filename" ]; then
            echo "$filename already exists" >&2
            exit 1
        fi
    done
    "$toolchain/bin/$host_triplet-ar" r "$sysroot/usr/lib/lib$name.a"
done
