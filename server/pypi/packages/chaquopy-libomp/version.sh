#!/bin/bash
set -eu -o pipefail

toolchain=$(realpath $(dirname $AR)/..)

cd $toolchain/lib/clang
echo *
