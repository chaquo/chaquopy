Deliberate syntax error: this file has not been updated for the current structure of
chaquopy-target.

# This image takes the same command-line arguments as build-wheel.py, except for `--toolchain`,
# which should be omitted.
#
# Each run will generate one wheel file in the directory /root/pypi/dist, which is structured
# as a PyPI respository. If a package requires other packages to build against, then this
# directory must be supplied as a mount or a volume which already contains those packages'
# wheel files.

FROM chaquopy-target

# OpenCV requires Python 2 even when building for Python 3: see its patch.
#
# TensorFlow requires python3-dev because it builds various things for the build platform: see
# its README.
RUN apt-get update && \
    apt-get install -y python python3-dev python3-pip && \
    ln -sf python3 /usr/bin/python

# Miscellaneous build tools
RUN apt-get update && \
    apt-get install -y automake cmake git libtool ninja-build patch

# protoc (for PyTorch): needs to be exactly this version.
RUN version=3.6.1 && \
    wget https://github.com/protocolbuffers/protobuf/releases/download/v$version/protoc-$version-linux-x86_64.zip && \
    unzip -d /usr protoc-*.zip && \
    rm protoc-*.zip

# Bazel (for TensorFlow)
RUN apt-get update && \
    apt-get -y install pkg-config zip g++ zlib1g-dev unzip && \
    version=0.21.0 && \
    filename=bazel-$version-installer-linux-x86_64.sh && \
    wget https://github.com/bazelbuild/bazel/releases/download/$version/$filename && \
    chmod +x $filename && \
    ./$filename && \
    rm $filename

COPY requirements.txt pypi/
RUN pip3 install -r pypi/requirements.txt

COPY . pypi/
ENV LC_ALL="C.UTF-8"
ENTRYPOINT ["pypi/docker-entrypoint.sh"]
