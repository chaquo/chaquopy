#!/bin/bash
set -eu

# Set configure variables which would otherwise fail with the error "cannot run test program
# while cross compiling".
export hdf5_cv_ldouble_to_long_special=no
export hdf5_cv_long_to_ldouble_special=no
export hdf5_cv_ldouble_to_llong_accurate=yes
export hdf5_cv_llong_to_ldouble_correct=yes

# See README.md
if [ -e $RECIPE_DIR/generated/$CHAQUOPY_ABI ]; then
    cp $RECIPE_DIR/generated/$CHAQUOPY_ABI/* src
else
    # The following is necessary to generate runnable H5detect and H5make_libsettings
    # executables. Android 5.0 and later only supports position-independent executables, but
    # build-wheel.py doesn't include these flags (see its source for why).
    export LDFLAGS="$LDFLAGS -fPIE -pie"
fi

# Some internal libraries can't be built with this flag.
LDFLAGS=$(echo $LDFLAGS | sed 's/-Wl,--no-undefined//')

./configure --host=$HOST --prefix=$PREFIX
make -j $CPU_COUNT
make install

rm -r $PREFIX/{bin,share}
rm $PREFIX/lib/{*.a,*.la}
