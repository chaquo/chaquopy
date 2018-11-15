FROM debian:stretch-20180831
SHELL ["/bin/bash", "-c"]
WORKDIR /root

RUN echo "progress=dot:giga" > .wgetrc

# Crystax NDK: reduce image size by removing the things we're going to rebuild.
RUN apt-get update && \
    apt-get install -y wget xz-utils
RUN filename=crystax-ndk-10.3.2-linux-x86_64.tar.xz && \
    wget https://www.crystax.net/download/$filename && \
    tar -xf $filename && \
    rm $filename && \
    mv crystax-ndk-* crystax && \
    rm -r crystax/toolchains crystax/sources/{crystax,openssl,python}

# Rebuild toolchains to add a Fortran compiler for OpenBLAS and SciPy.
RUN apt-get update && \
    apt-get install -y bison bzip2 file flex g++ gcc m4 make ruby texinfo
COPY platform src/crystax/platform
COPY toolchain src/crystax/toolchain
COPY vendor src/crystax/vendor
RUN src/crystax/platform/ndk/build/tools/build-host-prebuilts.sh \
        --verbose --systems=linux-x86_64 --arch=arm,arm64,x86 \
        src/crystax/toolchain && \
    rm -r /tmp/ndk-* && \
    mv src/crystax/platform/ndk/toolchains crystax

ENV ABIS="armeabi-v7a,arm64-v8a,x86"

# Rebuild libcrystax to fix several bugs (see commit history of `crystax/platform/ndk`).
#
# armeabi and armeabi-v7a-hard are both required by make-standalone-toolchain.sh. Also,
# armeabi is required for OpenBLAS: see pypi/packages/chaquopy-openblas/build.sh.
RUN NDK=$(pwd)/crystax \
    ABIS=$ABIS,armeabi,armeabi-v7a-hard \
    make -j $(nproc) -C src/crystax/platform/ndk/sources/crystax && \
    mv src/crystax/platform/ndk/sources/crystax crystax/sources
