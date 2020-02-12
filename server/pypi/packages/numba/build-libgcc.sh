#!/bin/bash
set -eu

# On armeabi-v7a, some of the functions in numba/runtime (which are JITed whether the program
# needs them or not) require some atomic support functions from libgcc. Normally it would find
# these in libgcc_s, but that doesn't exist on Android.
#
# The symbols are HIDDEN in libgcc.a, which would stop them being visible in the .so. We fix
# this with the `rebind` tool in this directory, which was built from
# https://github.com/BR903/ELFkickers/tree/e1af22cc152abc9e9c8d28e8011fd39d33e8e3c1.

output=$(realpath ${1:?})

tmp_dir=$(mktemp -d)
cd $tmp_dir

toolchain=$(realpath $(dirname $CC)/..)
files="linux-atomic.o"
ar x $toolchain/lib/gcc/arm-linux-androideabi/4.9.x/armv7-a/thumb/libgcc.a $files
for file in $files; do
    nm $file | grep ' T ' | sed 's/^.* T //' | $RECIPE_DIR/rebind --visibility default $file
done
$CC $LDFLAGS -shared -o $output $files

rm -r $tmp_dir
