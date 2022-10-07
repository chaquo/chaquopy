#!/bin/bash
set -eux

python=${1:?}
abi=${2:?}

cd $(dirname $0)/../..
./build-wheel.py --python $python --abi $abi --no-build cryptography

python_tag=cp$(echo $python | sed 's/\.//')
abi_tag=$(echo $abi | sed 's/-/_/')
reqs_dir=packages/cryptography/build/3.4.8/$python_tag-$python_tag-android_21_$abi_tag/requirements/chaquopy
rm -r $reqs_dir/include/openssl
rm $reqs_dir/lib/lib{crypto,ssl}*

prefix_dir=../../target/prefix/$abi
cp -a $prefix_dir/include/openssl $reqs_dir/include
cp -a $prefix_dir/lib/*.a $reqs_dir/lib

./build-wheel.py --python $python --abi $abi --no-unpack --no-reqs cryptography
