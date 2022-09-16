# This should match the version of ndkDir in product/runtime/build.gradle.
#
# When moving to a new version of the NDK, carefully review the following:
# * The release notes (https://developer.android.com/ndk/downloads/revision_history)
# * https://android.googlesource.com/platform/ndk/+/ndk-release-rXX/docs/BuildSystemMaintainers.md,
#   where XX is the NDK version. Do a diff against the version you're upgrading from.
ndk_version=22.1.7171670
ndk=${ANDROID_HOME:?}/ndk/$ndk_version
if ! [ -e $ndk ]; then
    yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "ndk;$ndk_version"
fi

abi=$(basename $prefix)
case $abi in
    armeabi-v7a)
        host_triplet=arm-linux-androideabi
        clang_triplet=armv7a-linux-androideabi
        ;;
    arm64-v8a)
        host_triplet=aarch64-linux-android
        ;;
    x86)
        host_triplet=i686-linux-android
        ;;
    x86_64)
        host_triplet=x86_64-linux-android
        ;;
    *)
        echo "Unknown ABI: '$abi'"
        ;;
esac

# This should match MIN_SDK_VERSION in Common.java.
api_level=21

# These variables are based on BuildSystemMaintainers.md above, and
# $ndk/build/cmake/android.toolchain.cmake.
toolchain_bin="$ndk/toolchains/llvm/prebuilt/linux-x86_64/bin"
export AR="$toolchain_bin/llvm-ar"
export AS="$toolchain_bin/$host_triplet-as"
export CC="$toolchain_bin/${clang_triplet:-$host_triplet}$api_level-clang"
export CXX="${CC}++"
export LD="$toolchain_bin/ld"
export NM="$toolchain_bin/llvm-nm"
export RANLIB="$toolchain_bin/llvm-ranlib"
export READELF="$toolchain_bin/llvm-readelf"
export STRIP="$toolchain_bin/llvm-strip"

export CFLAGS="-I $prefix/include"
export LDFLAGS="-L $prefix/lib \
-Wl,--exclude-libs,libgcc.a -Wl,--exclude-libs,libgcc_real.a -Wl,--exclude-libs,libunwind.a \
-Wl,--build-id=sha1 -Wl,--no-rosegment"

case $abi in
    armeabi-v7a)
        CFLAGS+=" -march=armv7-a -mthumb -mfpu=vfpv3-d16"
        ;;
    x86)
        # -mstackrealign is unnecessary because it's included in the clang launcher script
        # which is pointed to by $CC.
        ;;
esac

export PKG_CONFIG="pkg-config --define-prefix"
export PKG_CONFIG_LIBDIR="$prefix/lib/pkgconfig"
