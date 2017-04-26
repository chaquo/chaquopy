#/bin/bash
set -eu

crystax=~/crystax-ndk-10.3.2
crystax_python=$crystax/sources/python

mkdir -p com/chaquo/python/target
short_ver=2.7
full_ver=2.7.10-0

for abi in arm64-v8a armeabi armeabi-v7a x86 x86_64; do
    zipfile=com/chaquo/python/target/target-$full_ver-$abi.zip
    rm -f $zipfile
    rm -rf tmp
    mkdir tmp
    cp $crystax_python/$short_ver/libs/$abi/libpython$short_ver.so tmp
    cp $crystax/sources/crystax/libs/$abi/libcrystax.so tmp
    zip -j $zipfile tmp/*
    rm -r tmp
done
cp $crystax_python/$short_ver/libs/x86/stdlib.zip com/chaquo/python/target/target-$full_ver-stdlib.zip

for f in $(find -name *zip); do
    sha1sum $f |cut -d' ' -f1 > $f.sha1;
done
