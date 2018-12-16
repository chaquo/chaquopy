FROM debian:stretch-20180831
SHELL ["/bin/bash", "-c"]
WORKDIR /root

RUN apt-get update && \
    apt-get install -y wget unzip
RUN echo "progress=dot:giga" > .wgetrc

# Not installing the NDK with sdkmanager, because there's no way to select a specific version
# to make the build reproducible.
RUN filename=android-ndk-r18b-linux-x86_64.zip && \
    wget https://dl.google.com/android/repository/$filename && \
    unzip -q $filename && \
    rm $filename && \
    mv android-ndk-* android-ndk

# Python 3.6 isn't included in this version of Debian, so use a third-party build.
RUN apt-get update && \
    wget https://github.com/chriskuehl/python3.6-debian-stretch/releases/download/v3.6.3-1-deb9u1/{python3.6,python3.6-dev,python3.6-minimal,libpython3.6,libpython3.6-dev,libpython3.6-minimal,libpython3.6-stdlib}_3.6.3-1.deb9u1_amd64.deb && \
    apt install -y ./*.deb && \
    rm *.deb && \
    ln -s python3.6 /usr/bin/python && \
    ln -s python3.6 /usr/bin/python3

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

# Python
COPY python target/python
COPY build-python.sh target/
RUN target/build-python.sh $toolchain
