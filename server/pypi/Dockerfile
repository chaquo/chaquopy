# This image takes the same command-line arguments as build-wheel.py. The required argument
# --toolchain should be given as "target/toolchains/<abi>".
#
# Each run will generate one wheel file in the directory /root/pypi/dist, which is structured
# as a PyPI respository. If a package requires other packages to build against, then this
# directory must be supplied as a mount or a volume which already contains those packages'
# wheel files.

FROM chaquopy-target

# Miscellaneous build tools
RUN apt-get update && \
    apt-get install -y automake cmake git libtool-bin ninja-build patch pkg-config swig

# protoc (for PyTorch): use newest version from third_party/protobuf/CHANGES.txt.
RUN version=3.11.4 && \
    wget https://github.com/protocolbuffers/protobuf/releases/download/v$version/protoc-$version-linux-x86_64.zip && \
    unzip -d /usr protoc-*.zip && \
    rm protoc-*.zip

# Bazel (for TensorFlow)
RUN wget https://github.com/bazelbuild/bazelisk/releases/download/v1.2.1/bazelisk-linux-amd64 && \
    mv bazelisk-linux-amd64 /usr/local/bin/bazel

# Rust (for Tokenizers)
RUN wget https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init && \
    chmod +x rustup-init && \
    ./rustup-init -y && \
    rm rustup-init
ENV PATH="/root/.cargo/bin:$PATH"

COPY requirements.txt pypi/
RUN pip3 install -r pypi/requirements.txt

COPY . pypi/
ENV LC_ALL="C.UTF-8"
ENTRYPOINT ["pypi/build-wheel.py"]
