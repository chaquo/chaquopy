#!/bin/bash
set -eu

# Bazel 0.15 is the minimum required (see WORKSPACE).
# Bazel 0.18 will remove support for tools/bazel.rc, which this version of TensorFlow depends
# on (https://github.com/bazelbuild/bazel/issues/4502).
bazel_ver="$(bazel version)"
if ! echo $bazel_ver | grep -E 'Build label: 0\.(15|16|17)'; then
    echo "Bazel version is not compatible: see build.sh"
    exit 1
fi

# The Python lib and include locations will be passed using environment variables below. All
# other flags are added to the CROSSTOOL file. Unknown lib and include flags are an error
# because, with bazel's very strict dependency tracking, merely adding them to CROSSTOOL will
# probably not be good enough.
compiler_flags=""
for flag in $CFLAGS; do
    if echo $flag | grep -q "^-I"; then
        if echo $flag | grep -q "sources/python"; then
            python_include_dir=$(echo $flag | sed 's/^..//')
        else
            echo "Unknown flag: $flag"; exit 1
        fi
    else
        compiler_flags+="compiler_flag: \"$flag\"  # Chaquopy: added by build.sh\n  "
    fi
done

linker_flags=""
for flag in $LDFLAGS; do
    if echo $flag | grep -q "^-L"; then
        if echo $flag | grep -q "sources/python"; then
            python_lib_dir=$(echo $flag | sed 's/^..//')
        else
            echo "Unknown flag: $flag"; exit 1
        fi
    elif echo $flag | grep -q "^-l"; then
        if echo $flag | grep -q "lpython"; then
            python_lib=$(echo $flag | sed 's/^..//')
        else
            echo "Unknown flag: $flag"; exit 1
        fi
    elif [ $flag = "-Wl,--no-undefined" ]; then
        # The secondary Python native modules (e.g.
        # tensorflow/contrib/framework/python/ops/_variable_ops.so) contain references to
        # TensorFlow symbols which will be satisfied at runtime by the main module
        # _pywrap_tensorflow_internal.so. So we remove --no-undefined from the general linker
        # flags, and reintroduce it for the main module in tensorflow/tensorflow.bzl.
        true
    else
        linker_flags+="linker_flag: \"$flag\"  # Chaquopy: added by build.sh\n  "
    fi
done

rm -rf chaquopy  # For testing with build-wheel.py --no-unpack.
mkdir chaquopy
cp -a $RECIPE_DIR/crosstool chaquopy
mv chaquopy/crosstool/CROSSTOOL.tpl chaquopy/crosstool/CROSSTOOL
for cmd in "s|%{CHAQUOPY_TOOL_PREFIX}|$(echo $CC | sed 's/gcc$//')|g" \
           "s|%{CHAQUOPY_TOOLCHAIN}|$(realpath $(dirname $CC)/..)|g" \
           "s|%{CHAQUOPY_COMPILER_FLAGS}|$compiler_flags|g" \
           "s|%{CHAQUOPY_LINKER_FLAGS}|$linker_flags|g"; do
    sed -i "$cmd" chaquopy/crosstool/CROSSTOOL
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
# Optional features are disabled for now to simplify the situation. Set all variables on the
# command line rather than exporting, in case they affect the main build in some way.
PYTHON_BIN_PATH=$(which python$CHAQUOPY_PYTHON) \
    TF_NEED_GCP="0" TF_NEED_HDFS="0" TF_NEED_AWS="0" TF_NEED_KAFKA="0" \
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

for cmd in build cquery; do cat >>.tf_configure.bazelrc <<EOF

# The following environment variables are used by third_party/py/python_configure.bzl.
$cmd --action_env SRC_DIR=$SRC_DIR
$cmd --action_env CHAQUOPY_PYTHON_INCLUDE_DIR=$python_include_dir
$cmd --action_env CHAQUOPY_PYTHON_LIB_DIR=$python_lib_dir
$cmd --action_env CHAQUOPY_PYTHON_LIB=$python_lib
$cmd --crosstool_top=//chaquopy/crosstool
$cmd --cpu=chaquopy
$cmd --host_crosstool_top=@bazel_tools//tools/cpp:toolchain
$cmd --host_compilation_mode=fastbuild
$cmd --force_pic  # Prevent everything from being built both PIC and non-PIC.
EOF
done

rm -f *.whl  # For testing with build-wheel.py --no-unpack.
bazel build --config=opt --config=monolithic //tensorflow/tools/pip_package:build_pip_package
bazel-bin/tensorflow/tools/pip_package/build_pip_package .
unzip -q -d ../prefix *.whl
