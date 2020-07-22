# This image takes the same command-line arguments as build-wheel.py. The required argument
# --toolchain should be given as "target/toolchains/<abi>".
#
# Each run will generate one wheel file in the directory /root/pypi/dist, which is structured
# as a PyPI respository. If a package requires other packages to build against, then this
# directory must be supplied as a mount or a volume which already contains those packages'
# wheel files.

FROM chaquopy-target

# OpenCV requires Python 2 even when building for Python 3: see its patch.
RUN apt-get update && \
    apt-get install -y python && \
    ln -sf python3 /usr/bin/python

# Miscellaneous build tools
RUN apt-get update && \
    apt-get install -y automake cmake git libtool ninja-build patch patchelf swig

# protoc (for PyTorch): needs to be exactly this version.
RUN version=3.6.1 && \
    wget https://github.com/protocolbuffers/protobuf/releases/download/v$version/protoc-$version-linux-x86_64.zip && \
    unzip -d /usr protoc-*.zip && \
    rm protoc-*.zip

# Bazel (for TensorFlow)
RUN wget https://github.com/bazelbuild/bazelisk/releases/download/v1.2.1/bazelisk-linux-amd64 && \
    mv bazelisk-linux-amd64 /usr/local/bin/bazel

COPY requirements.txt pypi/
RUN pip3 install -r pypi/requirements.txt

COPY . pypi/
ENV LC_ALL="C.UTF-8"
ENTRYPOINT ["pypi/build-wheel.py"]
