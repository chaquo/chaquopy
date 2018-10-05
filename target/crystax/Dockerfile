FROM debian:stretch
SHELL ["/bin/bash", "-c"]

WORKDIR /root

# Install original Crystax NDK.
RUN apt-get update && \
    apt-get install -y wget xz-utils && \
    wget --progress=dot:giga \
        https://www.crystax.net/download/crystax-ndk-10.3.2-linux-x86_64.tar.xz && \
    tar -xf crystax-ndk-10.3.2-linux-x86_64.tar.xz && \
    rm crystax-ndk-10.3.2-linux-x86_64.tar.xz && \
    mv crystax-ndk-10.3.2 crystax

COPY platform src/crystax/platform
COPY toolchain src/crystax/toolchain
COPY vendor src/crystax/vendor

# Rebuild toolchains to add a Fortran compiler for OpenBLAS and SciPy.
RUN apt-get update && \
    apt-get install -y bison bzip2 file flex g++ gcc m4 make ruby texinfo && \
    src/crystax/platform/ndk/build/tools/build-host-prebuilts.sh \
        --verbose --systems=linux-x86_64 --arch=arm,arm64,x86 \
        src/crystax/toolchain && \
    rm -r /tmp/ndk- && \
    rm -r crystax/toolchains/*-4.9 && \
    mv src/crystax/platform/ndk/toolchains/*-4.9 crystax/toolchains

ENV ABIS="armeabi-v7a,arm64-v8a,x86"

# Rebuild libcrystax to fix several bugs (see commit history of `crystax/platform/ndk`).
RUN NDK=$(pwd)/crystax ABIS=$ABIS make -j $(nproc) -C src/crystax/platform/ndk/sources/crystax && \
    rm -r crystax/sources/crystax && \
    mv src/crystax/platform/ndk/sources/crystax crystax/sources

RUN rm -r src