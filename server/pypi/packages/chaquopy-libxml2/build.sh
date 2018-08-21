#!/bin/bash
set -eu

HOST_TRIPLET=$(basename $CC | sed 's/-gcc$//')
./configure --host=$HOST_TRIPLET --prefix=$PREFIX --without-python
make -j $CPU_COUNT
make install

rm -r $PREFIX/{bin,share}
rm -r $PREFIX/lib/{*.a,*.la,*.sh,cmake,pkgconfig}

# Remove the need to add an additional -I flag to build against it.
mv $PREFIX/include/libxml2/libxml $PREFIX/include
rmdir $PREFIX/include/libxml2
