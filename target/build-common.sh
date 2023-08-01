# This script must be sourced with the following variables already set:
#   * ANDROID_HOME: path to Android SDK
#   * prefix: path with `include` and `lib` subdirectories to add to CFLAGS and LDFLAGS.
#
# You may also override the following:
: ${abi:=$(basename $prefix)}
: ${api_level:=21}  # Should match MIN_SDK_VERSION in Common.java.

# When moving to a new version of the NDK, carefully review the following:
# * The release notes (https://developer.android.com/ndk/downloads/revision_history)
# * https://android.googlesource.com/platform/ndk/+/ndk-release-rXX/docs/BuildSystemMaintainers.md,
#   where XX is the NDK version. Do a diff against the version you're upgrading from.
ndk_version=22.1.7171670  # See ndkDir in product/runtime/build.gradle.
ndk=${ANDROID_HOME:?}/ndk/$ndk_version
if ! [ -e $ndk ]; then
    # Print all messages on stderr so they're visible when running within build-wheel.
    echo "Installing NDK: this may take several minutes" >&2
    yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "ndk;$ndk_version"
fi

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
        echo "Unknown ABI: '$abi'" >&2
        exit 1
        ;;
esac

# These variables are based on BuildSystemMaintainers.md above, and
# $ndk/build/cmake/android.toolchain.cmake.
toolchain="$ndk/toolchains/llvm/prebuilt/linux-x86_64"
export AR="$toolchain/bin/llvm-ar"
export AS="$toolchain/bin/$host_triplet-as"
export CC="$toolchain/bin/${clang_triplet:-$host_triplet}$api_level-clang"
export CXX="${CC}++"
export LD="$toolchain/bin/ld"
export NM="$toolchain/bin/llvm-nm"
export RANLIB="$toolchain/bin/llvm-ranlib"
export READELF="$toolchain/bin/llvm-readelf"
export STRIP="$toolchain/bin/llvm-strip"

export CFLAGS="-I${prefix:?}/include"
export LDFLAGS="-L${prefix:?}/lib \
-Wl,--exclude-libs,libgcc.a -Wl,--exclude-libs,libgcc_real.a -Wl,--exclude-libs,libunwind.a \
-Wl,--build-id=sha1 -Wl,--no-rosegment"

# Many packages get away with omitting this on standard Linux, but Android is stricter.
LDFLAGS+=" -lm"

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
