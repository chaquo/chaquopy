#!/bin/bash
set -eu

# Positional arguments:
#  * Maven directory to download into, e.g. /path/to/com/chaquo/python/target/3.10.6-3.
#    Must not already exist.

# Fail if target already exists: we don't want to overwrite things by accident.
mkdir -p $(dirname ${1:?})
mkdir $1
target_dir=$(cd $1 && pwd)

cd $target_dir
version=$(basename $target_dir)

# Set user-agent to circumvent Maven Central's block of wget.
# Redirect stderr to stdout, otherwise output gets mixed up in CI.
wget -r -l1 --no-parent --no-directories --accept .zip --progress dot:giga \
    -e robots=off --user-agent Mozilla/5.0 \
    https://repo.maven.apache.org/maven2/com/chaquo/python/target/$version/ 2>&1
