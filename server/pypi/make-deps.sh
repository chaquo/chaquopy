#!/bin/bash

mkdir -p logs/deps
rm -rf logs/deps/*

for pkg in \
    "chaquopy-freetype" \
    "chaquopy-libjpeg" \
    "chaquopy-libogg" \
    "chaquopy-libpng" \
    "chaquopy-libxml2" \
    "chaquopy-libiconv" \
    "chaquopy-curl" \
    "chaquopy-ta-lib" \
    "chaquopy-zbar" ; do
    python build-wheel.py --toolchain $1 --python $2 iOS $pkg 2>&1 | tee logs/deps/$pkg.log
done

echo
echo "========================================"
echo "Expected 9 modules; built $(find dist -name "*-py3-none-ios_12_0.whl" | sort | wc -l)"
