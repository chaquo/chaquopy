FROM debian:buster-20190228
SHELL ["/bin/bash", "-c"]
WORKDIR /root

RUN apt-get update && \
    apt-get install -y unzip wget
RUN echo "progress=dot:giga" > .wgetrc

# Not installing the NDK with sdkmanager, because there's no way to select a specific version
# to make the build reproducible.
RUN filename=android-ndk-r18b-linux-x86_64.zip && \
    wget https://dl.google.com/android/repository/$filename && \
    unzip -q $filename && \
    rm $filename && \
    mv android-ndk-* android-ndk

RUN apt-get update && \
    apt-get install -y python3 && \
    ln -sf python3 /usr/bin/python

ARG abi
RUN test -n "$abi"
ARG api
RUN test -n "$api"
ENV toolchain="/root/target/toolchains/$abi"
COPY build-toolchain.sh target/
RUN target/build-toolchain.sh android-ndk $abi $api

# Fortran compiler (for OpenBLAS and SciPy)
RUN apt-get update && \
    apt-get -y install bison flex g++ make
COPY gcc target/gcc
RUN cd target/gcc/gcc-4.9 && contrib/download_prerequisites
COPY build-fortran.sh build-common.sh target/
RUN target/build-fortran.sh $toolchain

COPY build-common-tools.sh target/

# OpenSSL
RUN apt-get update && \
    apt-get install -y perl-modules
COPY openssl target/openssl
COPY build-openssl.sh target/
RUN target/build-openssl.sh $toolchain

# SQLite
RUN apt-get update && \
    apt-get install -y gcc tclsh
COPY sqlite target/sqlite
COPY python/config.sub target/python/
COPY build-sqlite.sh target/
RUN target/build-sqlite.sh $toolchain

# libffi
COPY build-libffi.sh target/
RUN target/build-libffi.sh $toolchain

# Python
COPY python target/python
COPY build-python.sh target/
RUN target/build-python.sh $toolchain
