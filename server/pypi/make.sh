#!/bin/bash

mkdir -p logs/$2
rm -rf logs/$2/*

for pkg in \
    "cffi" \
    "numpy" \
    "aiohttp" \
    "argon2-cffi" \
    "backports-zoneinfo" \
    "bcrypt" \
    "bitarray" \
    "brotli" \
    "cryptography" \
    "cymem" \
    "cytoolz" \
    "editdistance" \
    "ephem" \
    "frozenlist" \
    "greenlet" \
    "kiwisolver" \
    "lru-dict" \
    "matplotlib" \
    "multidict" \
    "murmurhash" \
    "netifaces" \
    "pandas" \
    "pillow" \
    "preshed" \
    "pycrypto" \
    "pycurl" \
    "pynacl" \
    "pysha3" \
    "pywavelets" \
    "pyzbar" \
    "regex" \
    "ruamel-yaml-clib" \
    "scandir" \
    "spectrum" \
    "srsly" \
    "twisted" \
    "typed-ast" \
    "ujson" \
    "wordcloud" \
    "yarl" \
    "zstandard" ; do
    python build-wheel.py --toolchain $1 --python $2 iOS $pkg 2>&1 | tee logs/$2/$pkg.log
done

echo
echo "========================================"
echo "Expected 42 modules; built $(find dist -name "*-cp${2//./}-ios_12_0.whl" | sort | wc -l)"
