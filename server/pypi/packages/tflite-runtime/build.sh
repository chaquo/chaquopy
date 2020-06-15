#!/bin/bash
set -eu

tensorflow/lite/tools/pip_package/build_pip_package.sh
build_dir="/tmp/tflite_pip"
unzip -q -d ../prefix $build_dir/*/dist/*.whl
rm -r $build_dir
