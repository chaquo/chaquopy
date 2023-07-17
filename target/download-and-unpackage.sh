#!/bin/bash
set -eu

# Positional arguments:
#  * `prefix` directory to unpack into
#  * Version to download, including build number

this_dir=$(cd $(dirname $0) && pwd)
prefix_dir=$(cd ${1:?} && pwd)
version=${2:?}

tmp_dir="/tmp/download-and-unpackage-$$"
version_dir=$tmp_dir/$version
mkdir -p $version_dir
cd $version_dir
wget -r -l1 --no-directories --accept .zip -e robots=off --user-agent Mozilla/5.0 \
    https://repo.maven.apache.org/maven2/com/chaquo/python/target/$version

echo
echo Unpacking:
$this_dir/unpackage-target.sh $prefix_dir $version_dir

rm -rf $tmp_dir
