#!/bin/bash
set -eu

#
# See README.txt for instructions.
#

# The Python lib and include locations will be passed using environment variables below. All
# other flags are passed using --copt and --linkopt. Unknown include flags are an error
# because, with bazel's very strict dependency tracking, merely adding them to CROSSTOOL will
# probably not be good enough.
compiler_flags=""
in_idirafter="false"
for flag in $CFLAGS; do
    if [[ "$flag" =~ ^-I ]]; then
        echo "Unknown flag: $flag"; exit 1
    elif [ "$flag" = "-idirafter" ]; then
        in_idirafter="true"
    elif [ "$in_idirafter" = "true" ]; then
        if [[ "$flag" =~ include/python ]]; then
            python_include_dir="$flag"
            in_idirafter="false"
        else
            echo "Unknown flag: $flag"; exit 1
        fi
    else
        compiler_flags+=" $flag"
    fi
done

linker_flags=""
for flag in $LDFLAGS; do
    if [[ "$flag" =~ ^-lpython ]]; then
        python_lib=$(echo $flag | sed 's/^..//')
    elif [ $flag = "-Wl,--no-undefined" ]; then
        # We can't use this flag, because the secondary Python native modules (e.g.
        # tensorflow/contrib/framework/python/ops/_variable_ops.so) contain references to
        # TensorFlow symbols which will be satisfied at runtime by the main module
        # _pywrap_tensorflow_internal.so. So we remove it here, and patch the build files to
        # restore it for the main module and the libtensorflow_framework library.
        true
    else
        linker_flags+=" $flag"
    fi
done

rm -rf chaquopy  # For rerunning with build-wheel.py --no-unpack.
mkdir chaquopy
cp -a $RECIPE_DIR/crosstool chaquopy
for filename in chaquopy/crosstool/*; do
    for cmd in "s|%{CHAQUOPY_ABI}|$CHAQUOPY_ABI|g" \
               "s|%{CHAQUOPY_TRIPLET}|$(basename $AR | sed 's/-ar$//')|g" \
               "s|%{CHAQUOPY_TOOLCHAIN}|$(realpath $(dirname $CC)/..)|g"; do
        sed -i "$cmd" "$filename"
    done
done

# Since we're using the crosstool mechanism to define the target toolchain, we unset all of
# build-wheel.py's toolchain environment variables to prevent them affecting things which need
# to be built for the host. Currently CC is the only variable used by
# bazel/tools/cpp/cc_configure.bzl, but that may change in the future
# (https://github.com/bazelbuild/bazel/issues/5186).
unset AR ARFLAGS AS CC CFLAGS CPP CPPFLAGS CXX CXXFLAGS F77 F90 FARCH FC LD LDFLAGS LDSHARED \
      NM RANLIB READELF STRIP

# The only thing this script does is to create .tf_configure.bazelrc, and .bazelrc which
# includes it. "< /dev/null" causes defaults to be used for every question that isn't answered
# by the given environment variables: these questions and their default answers will appear
# on-screen.
#
# Some optional features are disabled to reduce APK size. Set all variables on the
# command line rather than exporting, in case they affect the main build in some way.
PYTHON_BIN_PATH=$(which python$CHAQUOPY_PYTHON) \
    TF_ENABLE_XLA="0" \
    ./configure < /dev/null

# The configure script adds -march=native to both the host and target compiler flags. This is
# obviously invalid for the target when cross compiling. It *should* be fine for the host, but
# on one server with GCC 6.3.0 I got the errors "unrecognizable insn" and "internal compiler
# error: in extract_insn, at recog.c:2287" at Eigen/src/Core/arch/AVX512/PacketMath.h:880:1.
sed -iE '/-march=native/d' .tf_configure.bazelrc

cat >>.tf_configure.bazelrc <<EOF

# Chaquopy added the rest

# --verbose_failures is technically redundant with --subcommands, but saves us having to search
# for the command when building with high parallelism.
build --subcommands
build --verbose_failures
EOF

for cmd in build cquery; do
    cat >>.tf_configure.bazelrc <<EOF

# Some optional features are disabled to reduce APK size.
$cmd --config=noaws --config=nogcp --config=nohdfs --config=nonccl

# See tensorflow/core/kernels/BUILD. This is necessary to work around
# external/mkl_dnn/src/common/utils.hpp:45:1: error: static_assert failed "Intel(R) MKL-DNN
# supports 64 bit only"
$cmd --define="tensorflow_mkldnn_contraction_kernel=0"

# The following environment variables are used by third_party/py/python_configure.bzl.
$cmd --action_env SRC_DIR=$SRC_DIR
$cmd --action_env CHAQUOPY_PYTHON_INCLUDE_DIR=$python_include_dir
$cmd --action_env CHAQUOPY_PYTHON_LIB=$python_lib

$cmd --crosstool_top=//chaquopy/crosstool
$cmd --cpu=$CHAQUOPY_ABI
$cmd --host_crosstool_top=@bazel_tools//tools/cpp:toolchain
$cmd --host_compilation_mode=fastbuild
$cmd --force_pic  # Prevent everything from being built both PIC and non-PIC.

# Since we're not using the standard crosstool, restore some important flags.
$cmd:opt --copt="-O2"
$cmd:opt --copt="-DNDEBUG"
$cmd --linkopt="-lstdc++"

# Despite the -W prefix, this is an error by default with Clang, e.g.
# tensorflow/core/kernels/sparse/sparse_matrix_components_op.cc:92:40: error:
# non-constant-expression cannot be narrowed from type 'long long' to 'int' in initializer
# list
$cmd --copt="-Wno-c++11-narrowing"

# From CFLAGS and LDFLAGS
EOF
    for flag in $compiler_flags; do
        echo $cmd --copt=$flag >>.tf_configure.bazelrc
    done
    for flag in $linker_flags; do
        echo $cmd --linkopt=$flag >>.tf_configure.bazelrc
    done
done

rm -f *.whl  # For rerunning with build-wheel.py --no-unpack.
bazel build --config=opt //tensorflow/tools/pip_package:build_pip_package
bazel-bin/tensorflow/tools/pip_package/build_pip_package .
unzip -q -d ../prefix *.whl
rm *.whl
mkdir -p ../prefix/chaquopy/lib
mv ../prefix/tensorflow_core/libtensorflow_framework.so.2 ../prefix/chaquopy/lib

# Generate a matching tensorflow-gpu wheel.
cd "$RECIPE_DIR/tensorflow-gpu"
dist_dir=$(realpath "../../../dist/tensorflow-gpu")
mkdir -p "$dist_dir"
./setup.py bdist_wheel --build-number $PKG_BUILDNUM --dist-dir "$dist_dir"
