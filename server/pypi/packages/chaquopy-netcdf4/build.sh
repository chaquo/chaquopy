#!/bin/bash
set -eu

export LIBS=-lz

# Some internal libraries can't be built with this flag.             
LDFLAGS=$(echo $LDFLAGS | sed 's/-Wl,--no-undefined//')

./configure --host=$HOST --disable-netcdf4 --disable-dap --disable-byterange
make -j $CPU_COUNT all
make install prefix=$PREFIX
