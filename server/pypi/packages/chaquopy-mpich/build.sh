#!/bin/bash
set -eu

# Otherwise we get "please unset F90/F90FLAGS and set FC/FCFLAGS instead and rerun configure
# again" even with --enable-fortran=no.
unset FC F90

HOST_TRIPLET=$(basename $CC | sed 's/-gcc$//')
./configure --host=$HOST_TRIPLET --prefix=$PREFIX --disable-cxx --enable-fortran=no --with-pm=no
make -j $CPU_COUNT
make install
