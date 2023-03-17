#!/bin/bash
set -eu

./configure --host=$HOST --prefix=$PREFIX --disable-static --disable-docs
make -j $CPU_COUNT
make install
