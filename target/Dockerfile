FROM debian:buster-20190228
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

ARG abis
RUN test -n "$abis"
ARG api
RUN test -n "$api"
COPY build-toolchain.sh target/
RUN for abi in $abis; do target/build-toolchain.sh android-sdk/ndk/* $abi $api; done

# Fortran compiler (for OpenBLAS and SciPy)
RUN apt-get update && \
    apt-get -y install bison flex g++ make
# TODO restore once all ABIs are enabled.
# COPY gcc target/gcc
# RUN cd target/gcc/gcc-4.9 && contrib/download_prerequisites
COPY build-fortran.sh build-common.sh target/
# RUN for abi in $abis; do target/build-fortran.sh target/toolchains/$abi; done

COPY build-common-tools.sh target/

# OpenSSL
RUN apt-get update && \
    apt-get install -y perl-modules
COPY openssl target/openssl
COPY build-openssl.sh target/
RUN for abi in $abis; do target/build-openssl.sh target/toolchains/$abi; done

# SQLite
RUN apt-get update && \
    apt-get install -y gcc tclsh
COPY sqlite target/sqlite
COPY python/config.sub target/python/
COPY build-sqlite.sh target/
RUN for abi in $abis; do target/build-sqlite.sh target/toolchains/$abi; done

# libffi
COPY build-libffi.sh target/
RUN for abi in $abis; do target/build-libffi.sh target/toolchains/$abi; done

# Python
COPY python target/python
COPY build-python.sh target/
RUN for abi in $abis; do target/build-python.sh target/toolchains/$abi; done
