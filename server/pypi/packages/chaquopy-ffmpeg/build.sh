#!/bin/bash
export ANDROID_SDK_HOME=$ANDROID_HOME
export ANDROID_NDK_HOME=$ANDROID_HOME/ndk/22.1.7171670

set -eu

./ffmpeg-android-maker.sh