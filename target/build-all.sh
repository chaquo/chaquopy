#!/bin/bash
set -eu

cd $(dirname $(realpath $0))

echo "This script needs to be updated to use https://github.com/beeware/cpython-android-source-deps"
exit 1

# Build libraries shared by all Python versions.
./for-each-abi.sh bzip2/build.sh 1.0.8
./for-each-abi.sh libffi/build.sh 3.4.4
./for-each-abi.sh sqlite/build.sh 2022 3390200
./for-each-abi.sh xz/build.sh 5.4.5

# Build all supported versions of Python, and generate `target` artifacts for Maven.
#
# For a given Python version, we can't change the OpenSSL major version after we've made
# the first release, because that would break binary compatibility with our existing
# builds of the `cryptography` package. Also, multiple OpenSSL versions can't coexist
# within the same include directory, because they use the same header file names. So we
# build each OpenSSL version immediately before all the Python versions that use it.

./for-each-abi.sh openssl/build.sh 1.1.1s
python/build-and-package.sh 3.8

./for-each-abi.sh openssl/build.sh 3.0.5
python/build-and-package.sh 3.9
python/build-and-package.sh 3.10
python/build-and-package.sh 3.11
python/build-and-package.sh 3.12
