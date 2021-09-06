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

# Redirect all compiler scripts to the target-specific ones. In NDK r19, these are the only
# ones which contain all the workarounds from
# https://android.googlesource.com/platform/ndk/+/ndk-release-r19/docs/BuildSystemMaintainers.md#additional-required-arguments,
# such as -mstackrealign for x86.
clang_target="$(echo $host_triplet | sed 's/^arm-/armv7a-/')$api"
for name in clang clang++; do
    # Used by cmake 3.16.3, which ignores the CC and CXX environment variables when it detects
    # an Android toolchain.
    ln -sf "$clang_target-$name" "$toolchain/bin/$name"

    # Used by build-common-tools.sh.
    ln -sf "$clang_target-$name" "$toolchain/bin/$host_triplet-$name"

    # Used by build-wheel.
    ln -sf "$clang_target-$name" $(echo "$toolchain/bin/$host_triplet-$name" |
                                   sed 's/clang/gcc/; s/gcc++/g++/')

    # Break what is now an infinite loop.
    sed -i.old 's|/clang|/clang90|' "$toolchain/bin/$clang_target-$name"
done

sys_include="$sysroot/usr/include"

function assert_in {
    if ! grep -q "$1" "$2"; then
        echo "'$1' not found in $2"
        exit 1
    fi
}

# Standalone toolchains with unified headers rely on a command line argument in the Clang
# launcher scripts to define __ANDROID_API__. If it's not defined, which will be the case
# during the Fortran build, api-level.h assumes we're working on an unreleased Android version
# and sets it to 10000, which could cause all kinds of problems
# (https://android.googlesource.com/platform/ndk/+/ndk-r15-release/docs/UnifiedHeaders.md).
header="$sys_include/android/api-level.h"
pattern="#define __ANDROID_API__ __ANDROID_API_FUTURE__"
replacement="#define __ANDROID_API__ $api  /* Chaquopy: see build-toolchain.sh */"
sed -i.old "s|$pattern|$replacement|" $header
assert_in "Chaquopy" "$header"

# Add missing locale implementations, based on android/platform/bionic/libc/bionic/locale.cpp.
header="$sys_include/locale.h"
sed -i.old 's|struct lconv\* localeconv(.*| \
/* Chaquopy: localeconv is not available until API level 21. */ \
#if __ANDROID_API__ < 21 \
#include <limits.h> \
static struct lconv g_locale = { \
    ".", "", "", "", "", "", "", "", "", "", CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, \
    CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX, CHAR_MAX \
}; \
static struct lconv* localeconv(void) { return \&g_locale; } \
#else \
& \
#endif|;

s|char\* setlocale(.*| \
/* Chaquopy: setlocale always fails before API 21. */ \
#if __ANDROID_API__ < 21 \
static char *setlocale(int category, const char *locale) { return "C.UTF-8"; } \
#else \
& \
#endif|;
' "$header"
for name in localeconv setlocale; do assert_in "Chaquopy: $name" "$header"; done

# Before API level 21, some of the wchar functions simply cast wchar_t* to char* and then call
# the 8-bit string functions (see first revision of
# android/platform/bionic/libc/bionic/wchar.cpp). We disable any of these broken functions
# which write to a wchar_t* string, because their failure to write a 16-bit null terminator may
# cause a buffer overflow in the caller.
header="$sys_include/wchar.h"
sed -i.old 's|wchar_t\* fgetws(.*| \
/* Chaquopy: fgetws is unsafe before API 21. */ \
#if __ANDROID_API__ < 21 \
#include <errno.h> \
static wchar_t* fgetws(wchar_t* __buf, int __size, FILE* __fp) { \
    errno = ENOTSUP; \
    return NULL; \
} \
#else \
& \
#endif|;

s|size_t mbsrtowcs(.*| \
/* Chaquopy: mbsrtowcs is unsafe before API 21. */ \
#if __ANDROID_API__ < 21 \
static size_t mbsrtowcs(wchar_t* __dst, const char** __src, size_t __dst_n, mbstate_t* __ps) { \
    errno = ENOTSUP; \
    return (size_t)-1; \
} \
#else \
& \
#endif|;

s|size_t wcsftime(.*| \
/* Chaquopy: wcsftime is unsafe before API 21. Unlike the other functions, we cannot provide a \
   stub because the function has no way of reporting an error. It can return zero to indicate \
   the buffer is too small, but that could cause the caller to keep trying with an \
   ever-increasing buffer size. */ \
#if __ANDROID_API__ >= 21 \
& \
#endif|;
' "$header"
for name in fgetws mbsrtowcs wcsftime; do assert_in "Chaquopy: $name" "$header"; done

# Prevent disabled functions from being referenced in the C++ headers.
header="$sys_include/c++/v1/cwchar"
sed -i.old 's|using ::wcsftime;| \
/* Chaquopy: wcsftime is unsafe before API 21: see sysroot/usr/include/wchar.h. */ \
#if __ANDROID_API__ >= 21 \
& \
#endif|;
' "$header"
assert_in "Chaquopy: wcsftime" "$header"

header="$sys_include/stdlib.h"
sed -i.old 's|size_t mbstowcs(.*| \
/* Chaquopy: mbstowcs is unsafe before API 21. */ \
#if __ANDROID_API__ < 21 \
#include <errno.h> \
static size_t mbstowcs(wchar_t* __dst, const char* __src, size_t __n) { \
    errno = ENOTSUP; \
    return (size_t)-1; \
} \
#else \
& \
#endif|;
' "$header"
assert_in "Chaquopy: mbstowcs" "$header"

# The compiler knows to look in the $host_triplet/$api subdirectory, but most build systems
# won't. For example, python/setup.py expects to find libz.so here.
cd "$sysroot/usr/lib"
ln -s $host_triplet/$api/* .

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
    "$toolchain/bin/$host_triplet-ar" rc "$sysroot/usr/lib/lib$name.a"
done
