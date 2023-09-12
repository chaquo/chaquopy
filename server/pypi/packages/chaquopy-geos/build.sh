#!/bin/bash
set -eu

config_args=""
if [ "$HOST" = "arm-linux-androideabi" ]; then
    # On this ABI only, we get the following linker errors:
    #
    # ld: error: noding/.libs/libnoding.a(BasicSegmentString.o): multiple definition of 'typeinfo for geos::noding::BasicSegmentString'
    # ld: .libs/inlines.o: previous definition here
    # ld: error: noding/.libs/libnoding.a(BasicSegmentString.o): multiple definition of 'typeinfo name for geos::noding::BasicSegmentString'
    # ld: .libs/inlines.o: previous definition here
    # ld: error: noding/.libs/libnoding.a(BasicSegmentString.o): multiple definition of 'vtable for geos::noding::BasicSegmentString'
    # ld: .libs/inlines.o: previous definition here
    config_args+=" --disable-inline"
fi

./configure --host=$HOST --prefix=$PREFIX $config_args
make -j $CPU_COUNT
make install

rm -r $PREFIX/bin
rm $PREFIX/lib/*.a

# As recommended by the documentation, most users of this library link against libgeos_c, which
# has a copy of libgeos built into it.
rm $PREFIX/lib/{libgeos-*.so,libgeos.la}
