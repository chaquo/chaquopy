# This script must be sourced with the following variables already set:
#   * ANDROID_HOME: path to Android SDK
#   * prefix: path with `include` and `lib` subdirectories to add to CFLAGS and LDFLAGS.
#
# You may also override the following:
: ${abi:=$(basename $prefix)}
: ${api_level:=21}  # Should match MIN_SDK_VERSION in Common.java.

# Print all messages on stderr so they're visible when running within build-wheel.
log() {
    echo "$1" >&2
}

fail() {
    log "$1"
    exit 1
}

# When moving to a new version of the NDK, carefully review the following:
#
# * The release notes (https://developer.android.com/ndk/downloads/revision_history)
#
# * https://android.googlesource.com/platform/ndk/+/ndk-release-rXX/docs/BuildSystemMaintainers.md,
#   where XX is the NDK version. Do a diff against the version you're upgrading from.
#
# * According to https://github.com/kivy/python-for-android/pull/2615, the mzakharo
#   build of gfortran is not compatible with NDK version 23, which is the version in
#   which they removed the GNU binutils.
ndk_version=22.1.7171670  # See ndkDir in product/runtime/build.gradle.

ndk=${ANDROID_HOME:?}/ndk/$ndk_version
if ! [ -e $ndk ]; then
    log "Installing NDK: this may take several minutes"
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
        fail "Unknown ABI: '$abi'"
        ;;
esac

# These variables are based on BuildSystemMaintainers.md above, and
# $ndk/build/cmake/android.toolchain.cmake.
toolchain=$(echo $ndk/toolchains/llvm/prebuilt/*)
export AR="$toolchain/bin/llvm-ar"
export AS="$toolchain/bin/$host_triplet-as"
export CC="$toolchain/bin/${clang_triplet:-$host_triplet}$api_level-clang"
export CXX="${CC}++"
export LD="$toolchain/bin/ld"
export NM="$toolchain/bin/llvm-nm"
export RANLIB="$toolchain/bin/llvm-ranlib"
export READELF="$toolchain/bin/llvm-readelf"
export STRIP="$toolchain/bin/llvm-strip"

# The quotes make sure the wildcard in the `toolchain` assignment has been expanded.
for path in "$AR" "$AS" "$CC" "$CXX" "$LD" "$NM" "$RANLIB" "$READELF" "$STRIP"; do
    if ! [ -e "$path" ]; then
        fail "$path does not exist"
    fi
done

# Use -idirafter so that package-specified -I directories take priority. For example,
# grpcio provides its own BoringSSL headers which must be used rather than our OpenSSL.
export CFLAGS="-idirafter ${prefix:?}/include"
export LDFLAGS="-L${prefix:?}/lib \
-Wl,--exclude-libs,libgcc.a -Wl,--exclude-libs,libgcc_real.a -Wl,--exclude-libs,libunwind.a \
-Wl,--build-id=sha1 -Wl,--no-rosegment"

# Many packages get away with omitting this on standard Linux, but Android is stricter.
LDFLAGS+=" -lm"

case $abi in
    armeabi-v7a)
        CFLAGS+=" -march=armv7-a -mthumb"
        ;;
    x86)
        # -mstackrealign is unnecessary because it's included in the clang launcher script
        # which is pointed to by $CC.
        ;;
esac

export PKG_CONFIG="pkg-config --define-prefix"
export PKG_CONFIG_LIBDIR="$prefix/lib/pkgconfig"

# conda-build variable name
if [ $(uname) = "Darwin" ]; then
    export CPU_COUNT=$(sysctl -n hw.ncpu)
else
    export CPU_COUNT=$(nproc)
fi
