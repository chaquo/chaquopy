#!/bin/bash
set -eu


# FIXME before attempting clean build:
# * check all changes are in patches/
# * update build number
# * Try adding --force_pic (which also prevents duplication in host builds) and restoring
#  `needsPic: true` in CROSSTOOL.tpl.


# Extract the Python lib and include locations, and pass them to
# third_party/py/python_configure.bzl using environment variables. All other flags are added to
# the CROSSTOOL file. Unknown lib and include flags are an error because, with bazel's very
# strict dependency tracking, merely adding them to CROSSTOOL will probably not be good enough.
compiler_flags=""
for flag in $CFLAGS; do
    if echo $flag | grep -q "^-I"; then
        if echo $flag | grep -q "sources/python"; then
            export CHAQUOPY_PYTHON_INCLUDE_DIR=$(echo $flag | sed 's/^..//')
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
            export CHAQUOPY_PYTHON_LIB_DIR=$(echo $flag | sed 's/^..//')
        else
            echo "Unknown flag: $flag"; exit 1
        fi
    elif echo $flag | grep -q "^-l"; then
        if echo $flag | grep -q "lpython"; then
            export CHAQUOPY_PYTHON_LIB=$(echo $flag | sed 's/^..//')
        else
            echo "Unknown flag: $flag"; exit 1
        fi
    elif [ $flag = "-Wl,--no-undefined" ]; then
        # Some libraries have deliberately incomplete dependencies (see comment at top of
        # tensorflow/core/BUILD).
        true
    else
        linker_flags+="linker_flag: \"$flag\"  # Chaquopy: added by build.sh\n  "
    fi
done

# set -u will assert that all variables have been assigned.
echo $CHAQUOPY_PYTHON_INCLUDE_DIR $CHAQUOPY_PYTHON_LIB_DIR $CHAQUOPY_PYTHON_LIB > /dev/null

rm -rf chaquopy
mkdir chaquopy
cp -a $RECIPE_DIR/crosstool chaquopy
mv chaquopy/crosstool/CROSSTOOL.tpl chaquopy/crosstool/CROSSTOOL
for cmd in "s|%{CHAQUOPY_TOOL_PREFIX}|$(echo $CC | sed 's/gcc$//')|g" \
           "s|%{CHAQUOPY_TOOLCHAIN}|$(realpath $(dirname $CC)/..)|g" \
           "s|%{CHAQUOPY_COMPILER_FLAGS}|$compiler_flags|g" \
           "s|%{CHAQUOPY_LINKER_FLAGS}|$linker_flags|g"; do
    sed -i "$cmd" chaquopy/crosstool/CROSSTOOL
done

# Bazel 0.15 is the minimum required (see WORKSPACE).
# Bazel 0.18 will remove support for tools/bazel.rc, which this version of TensorFlow depends
# on (https://github.com/bazelbuild/bazel/issues/4502).
if ! bazel version | grep -E 'Build label: 0\.(15|16|17)'; then
    echo "Bazel version is not compatible: see build.sh"
    exit 1
fi

# The build includes many tools like protoc which have to be built for the build platform
# rather than the target platform. Since we're using the crosstool mechanism, we can unset all
# of build-wheel.py's toolchain environment variables to prevent them affecting these things.
# Currently CC is the only variable used by bazel/tools/cpp/cc_configure.bzl, but that may
# change in the future (https://github.com/bazelbuild/bazel/issues/5186).
unset AR ARFLAGS AS CC CFLAGS CPP CPPFLAGS CXX CXXFLAGS F77 F90 FARCH FC LD LDFLAGS LDSHARED \
      NM RANLIB READELF STRIP

# The only thing this script does is to create .tf_configure.bazelrc, and .bazelrc which
# includes it. "< /dev/null" causes defaults to be used for every question that isn't answered
# by the given environment variables: these questions and their default answers will appear
# on-screen.
#
# Optional features are disabled for now to simplify the situation. We also remove the default
# CC_OPT_FLAGS of '-march=native', which is not valid for cross-compiling. An empty string will
# use the default, but a whitespace string will disable it.
#
# Set all variables on the command line rather than exporting, in case they affect the main
# build in some way.
TF_NEED_GCP="0" TF_NEED_HDFS="0" TF_NEED_AWS="0" TF_NEED_KAFKA="0" CC_OPT_FLAGS=" " \
    ./configure < /dev/null

# --verbose_failures is technically redundant with --subcommands, but saves us having to search
# for the command when building with high parallelism.
bazel build --subcommands --verbose_failures \
    --config=opt \
    --crosstool_top=//chaquopy/crosstool --cpu=chaquopy \
    --host_crosstool_top=@bazel_tools//tools/cpp:toolchain --host_compilation_mode=fastbuild \
    //tensorflow/tools/pip_package:build_pip_package



# FIXME running this script as follows will build a .whl file within the /tmp/tensorflow_pkg
# directory:
# bazel-bin/tensorflow/tools/pip_package/build_pip_package /tmp/tensorflow_pkg

# FIXME get build-wheel to post-process this whl.


#################

# https://stackoverflow.com/questions/42861431/tensorflow-on-android-with-python-bindings
# https://www.tensorflow.org/install/install_sources
# [Building TensorFlow from source](https://gist.github.com/kmhofmann/e368a2ebba05f807fa1a90b3bf9a1e03)
# https://longervision.github.io/2018/07/10/DeepLearning/tensorflow-keras-build-from-source/


# Official Android builds for Java at
# https://bintray.com/google/tensorflow/tensorflow#files/org%2Ftensorflow%2Ftensorflow-android
# seem to contain a cut-down "TensorFlow Inference Interface" native library, so we probably
# can't build a wheel from that.


# Linux .whl contains 44 .so files, but most of them are in contrib so are probably optional.
# The remaining ones are:
#
# 16893032  2018-08-23 20:49   tensorflow-1.10.1.data/purelib/tensorflow/libtensorflow_framework.so
# 3881512   2018-08-23 20:50   tensorflow-1.10.1.data/purelib/tensorflow/include/external/protobuf_archive/python/google/protobuf/pyext/_message.so
# 8112      2018-08-23 20:50   tensorflow-1.10.1.data/purelib/tensorflow/include/external/protobuf_archive/python/google/protobuf/internal/_api_implementation.so
# 123959784 2018-08-23 20:49   tensorflow-1.10.1.data/purelib/tensorflow/python/_pywrap_tensorflow_internal.so
# 111760    2018-08-23 20:37   tensorflow-1.10.1.data/purelib/tensorflow/python/framework/fast_tensor_util.so
#
