#!/bin/bash
set -eu

export CROSS="1"
export HOSTCC="cc"

# "If your application is already multi-threaded, it will conflict with OpenBLAS
# multi-threading. Thus, you must set OpenBLAS to use single thread."
# (https://github.com/xianyi/OpenBLAS/wiki/faq#multi-threaded)
export USE_THREAD=0

# "You are setting NUM_THREADS because eventually it is used to calculate NUM_BUFFERS,
# regardless of OpenBLAS being single threaded or multithreaded. When you call an API like
# SGEMM, it needs its own buffers to work on. So if you have a multithreaded program and you
# call SGEMM from multiple threads at the same, each invocation of SGEMM will require its own
# buffer." (https://github.com/xianyi/OpenBLAS/issues/1141#issuecomment-291822374)
#
# NUM_BUFFERS = NUM_THREADS * 2, so the actual limit on concurrent threads is 16. Exceeding
# this limit will give the error "Program is Terminated. Because you tried to allocate too many
# memory regions."
export NUM_THREADS=8

case $CHAQUOPY_ABI in
    armeabi-v7a)
        # OpenBLAS ARMv7 build requires VFPv3-D32
        # (https://github.com/xianyi/OpenBLAS/issues/388 and
        # https://github.com/xianyi/OpenBLAS/issues/662), which in practice always seems
        # to come with NEON (aka "Advanced SIMD"), which requires it. The Android
        # armeabi-v7a ABI only guarantees NEON on API level 21 and higher, so we
        # currently target ARMv6:
        #
        # * https://developer.android.com/ndk/guides/abis.html
        # * https://developer.android.com/ndk/guides/cpu-arm-neon.html
        # * https://source.android.com/compatibility/cdd)
        export TARGET="ARMV6"
        export ARM_SOFTFP_ABI="1"

        # Update assembly syntax for Clang (https://github.com/xianyi/OpenBLAS/issues/1774).
        script='s/fldmias/vldmia.f32/; s/fldmiad/vldmia.f64/; s/fstmias/vstmia.f32/; s/fstmiad/vstmia.f64/'
        find kernel/arm -name '*.S' | xargs sed -i "$script"
        ;;

    arm64-v8a)
        export TARGET="ARMV8"
        ;;

    x86)
        export TARGET="ATOM"
        ;;

    x86_64)
        # This corresponds to the instruction set extensions listed at
        # https://developer.android.com/ndk/guides/abis#86-64.
        export TARGET="NEHALEM"
        ;;

    *)
        echo "Unknown ABI '$CHAQUOPY_ABI'"
        exit 1
        ;;
esac

# The Makefile assumes that all build tools have the same path prefix as $CC.
make -j "$CPU_COUNT" AR="$AR" AS="$AS" CC="$CC" CXX="$CXX" LD="$LD" NM="$NM" \
     RANLIB="$RANLIB" READELF="$READELF" STRIP="$STRIP"

make install  # The PREFIX environment variable will be respected.
cd $PREFIX/lib
rm *.a
find -type l | xargs rm
mv *.so libopenblas.so
