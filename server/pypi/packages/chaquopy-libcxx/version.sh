#!/bin/bash
set -eu -o pipefail

toolchain=$(realpath $(dirname $AR)/..)

pattern='^ *# *define +_LIBCPP_VERSION +([0-9]+)$'

grep -E "$pattern" "$toolchain/sysroot/usr/include/c++/v1/__config" |
    sed -E "s/$pattern/\1/"
