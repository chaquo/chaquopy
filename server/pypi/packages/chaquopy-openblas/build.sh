#!/bin/bash
set -eu

case $CHAQUOPY_ABI in
    iphoneos_arm64)
        TARGET="ARMV8"
        ARCH="arm64"
        SYSROOT_PATH="$(xcrun -sdk iphoneos -show-sdk-path)"
        ;;

    iphonesimulator_arm64)
        TARGET="ARMV8"
        ARCH="arm64"
        SYSROOT_PATH="$(xcrun -sdk iphonesimulator -show-sdk-path)"
        ;;

    iphonesimulator_x86_64)
        # This corresponds to the instruction set extensions listed at
        # https://developer.android.com/ndk/guides/abis#86-64.
        TARGET="NEHALEM"
        ARCH="x86_64"
        SYSROOT_PATH="$(xcrun -sdk iphonesimulator -show-sdk-path)"
        ;;

    *)
        echo "Unknown ABI '$CHAQUOPY_ABI'"
        exit 1
        ;;
esac

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

TOOLCHAIN_PATH=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin
make TARGET=${TARGET} BINARY=64 HOSTCC=clang CC="$TOOLCHAIN_PATH/clang -isysroot $SYSROOT_PATH -arch ${ARCH} -miphoneos-version-min=12.0 -O2" NOFORTRAN=1 libs
make install  # The PREFIX environment variable will be respected.
