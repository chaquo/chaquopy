#!/bin/bash
set -eu

# https://stackoverflow.com/a/33279062
touch aclocal.m4 configure Makefile.am Makefile.in

./configure --host=$HOST --disable-static --disable-openmp --disable-examples
make -j $CPU_COUNT
make install prefix=$PREFIX

rm -rf $PREFIX/{bin,share}
