FROM debian:bullseye-20191224
SHELL ["/bin/bash", "-c"]
WORKDIR /root

RUN apt-get update && \
    apt-get install -y unzip wget
RUN echo "progress=dot:giga" > .wgetrc

RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    ln -sf python3 /usr/bin/python

# The current version of sdkmanager doesn't work with Java 9 or later
# (https://stackoverflow.com/a/53619947), so install an Oracle Java 8 build instead
# (https://stackoverflow.com/a/10959815). A fix for this is planned to be released with Android
# Studio 3.6 (https://issuetracker.google.com/issues/67495440#comment20).
RUN wget -c --header "Cookie: oraclelicense=accept-securebackup-cookie" \
http://download.oracle.com/otn-pub/java/jdk/8u131-b11/d54c1d3a095b4ff2b6607d096fa80163/jdk-8u131-linux-x64.tar.gz && \
    tar -xf jdk*.tar.gz && \
    ( for name in java javac; do ln -s $(pwd)/jdk*/bin/$name /usr/bin/$name; done ) && \
    rm jdk*.tar.gz

RUN filename=sdk-tools-linux-4333796.zip && \
    wget https://dl.google.com/android/repository/$filename && \
    mkdir android-sdk && \
    unzip -q -d android-sdk $filename && \
    rm $filename

RUN yes | android-sdk/tools/bin/sdkmanager "ndk;18.1.5063045"

COPY build-toolchains.sh build-toolchain.sh build-common.sh target/
RUN target/build-toolchains.sh android-sdk/ndk/* "arm64-v8a armeabi-v7a x86 x86_64"
COPY for-each-abi.sh target/

# Fortran compiler (for OpenBLAS and SciPy). Although this is only required by the pypi
# Dockerfile, we put it here so we don't have to rebuild it every time we change the versions
# of any of the things below.
RUN apt-get update && \
    apt-get -y install bison flex g++ make
# TODO restore once all ABIs are enabled, and update .dockerignore.
# COPY gcc target/gcc
# RUN cd target/gcc/gcc-4.9 && contrib/download_prerequisites
# COPY build-fortran.sh target/
# RUN target/for-each-abi.sh target/build-fortran.sh

COPY build-common-tools.sh target/

# OpenSSL
RUN apt-get update && \
    apt-get install -y patchelf perl-modules
COPY openssl target/openssl
COPY build-openssl.sh target/
RUN target/for-each-abi.sh target/build-openssl.sh

# SQLite
RUN apt-get update && \
    apt-get install -y gcc tclsh
COPY sqlite target/sqlite
COPY python/config.sub target/python/
COPY build-sqlite.sh target/
RUN target/for-each-abi.sh target/build-sqlite.sh

# libffi
COPY build-libffi.sh target/
RUN target/for-each-abi.sh target/build-libffi.sh

# Python
RUN apt-get update && \
    apt-get install -y python3.8
COPY python target/python
COPY build-python.sh target/
RUN target/for-each-abi.sh target/build-python.sh
