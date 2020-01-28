tool_prefix="$toolchain/bin/$host_triplet"
export AR="$tool_prefix-ar"
export AS="$tool_prefix-as"
export CC="$tool_prefix-clang"
export CXX="$tool_prefix-clang++"
export LD="$tool_prefix-ld"
export NM="$tool_prefix-nm"
export RANLIB="$tool_prefix-ranlib"
export READELF="$tool_prefix-readelf"
export STRIP="$tool_prefix-strip"

# See build-wheel.py for explanations of these flags.
export CFLAGS=""
export LDFLAGS="-Wl,--exclude-libs,libgcc.a -Wl,--exclude-libs,libgcc_real.a -Wl,--exclude-libs,libunwind.a"

case $(basename $toolchain) in
    armeabi-v7a)
        CFLAGS+=" -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 -mthumb"
        LDFLAGS+=" -march=armv7-a -Wl,--fix-cortex-a8"
esac
