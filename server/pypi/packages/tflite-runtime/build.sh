#!/bin/bash
set -eu

# Values were determined by inspection of the Makefile.
export TENSORFLOW_TARGET="linux"
case $CHAQUOPY_ABI in
    armeabi-v7a)
        export TENSORFLOW_TARGET_ARCH="armv7l"
        ;;
    arm64-v8a)
        export TENSORFLOW_TARGET_ARCH="aarch64"
        ;;
    x86)
        export TENSORFLOW_TARGET_ARCH="x86_32"
        ;;
    x86_64)
        export TENSORFLOW_TARGET_ARCH="x86_64"
        ;;
    *)
        echo "Unknown ABI '$CHAQUOPY_ABI'"
        exit 1
        ;;
esac

pp_dir="tensorflow/lite/tools/pip_package"
$pp_dir/build_pip_package.sh
unzip -q -d ../prefix $pp_dir/gen/tflite_pip/python3/dist/*.whl
