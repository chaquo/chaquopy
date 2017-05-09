#!/bin/bash
set -eu

cd "$(dirname "$0")"
rm -rf javadoc
javadoc \
    -sourcepath 'src/main/java;C:\Program Files\Java\jdk1.8.0_121\src.zip' \
    -classpath 'C:\Users\smith\Programs\android-sdk\platforms\android-15\android.jar' \
    -Xdoclint:all,-missing \
    -link https://developer.android.com/reference/ \
    -stylesheetfile javadoc-chaquo.css \
    -d javadoc \
    com.chaquo.python
