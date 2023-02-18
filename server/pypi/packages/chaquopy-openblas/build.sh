#!/bin/bash
set -eu

export CROSS="1"
export CROSS_SUFFIX=$(echo $CC | sed 's/gcc$//')  # Actually a prefix
export HOSTCC="gcc"

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

# Prevent large local variables silently being treated as static, thus destroying thread-safety
# (http://wwwf.imperial.ac.uk/~mab201/20120814.html and
# https://github.com/xianyi/OpenBLAS/issues/477#issuecomment-222378330).
export FFLAGS="-frecursive"

case $CHAQUOPY_ABI in
    armeabi-v7a)
        # OpenBLAS ARMv7 build requires VFPv3-D32
        # (https://github.com/xianyi/OpenBLAS/issues/388 and
        # https://github.com/xianyi/OpenBLAS/issues/662), which in practice always seems to
        # come with NEON (aka "Advanced SIMD"), which requires it
        # (https://developer.android.com/ndk/guides/cpu-arm-neon.html). But the Android
        # armeabi-v7a ABI only guarantees VFPv3-D16
        # (https://developer.android.com/ndk/guides/abis.html). The Google compatibility
        # definition does require NEON from API level 23 (Android 6.0,
        # https://source.android.com/compatibility/cdd), but by the time it's safe to set that
        # as our minimum level, most people will probably be on ARMv8 anyway.
        #
        # There do exist devices with API level 15 or higher which are limited to VFPv3-D16,
        # but they are rare and probably from 2013 or older. One example is the Asus
        # Transformer TF101 (NOT the TF201 which I have), which has an Nvidia Tegra 2
        # processor. The NDK developers believe that that the Tegra 2 was the *only*
        # armeabi-v7a processor which didn't support NEON, and its number of active devices is
        # now so low that they've enabled NEON by default in NDK r21 and later
        # (https://github.com/android/ndk/issues/859). But we'll target ARMv6 for now anyway,
        # just to be safe.
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

make -j "$CPU_COUNT"

make install  # The PREFIX environment variable will be respected.
cd $PREFIX/lib
rm *.a
find -type l | xargs rm
mv *.so libopenblas.so
