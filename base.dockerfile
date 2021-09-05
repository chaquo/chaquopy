# This is the only version of Debian with official packages for both:
# * Java 8, used by the runtime tests (see javaHome in product/runtime/build.gradle).
# * Java 11, used by piptest because it's required by Android Gradle plugin 7.0 and later.
FROM debian:stretch-20210902
RUN echo "deb http://deb.debian.org/debian stretch-backports main" >> /etc/apt/sources.list

SHELL ["/bin/bash", "-c"]
WORKDIR /root

RUN apt-get update && \
    apt-get install -y openjdk-8-jdk-headless openjdk-11-jdk-headless unzip wget
RUN echo "progress=dot:giga" > .wgetrc

# Install the same minor Python version as Chaquopy uses.
RUN apt-get update && \
    apt-get install -y gcc libbz2-dev libffi-dev liblzma-dev libsqlite3-dev libssl-dev \
                       zlib1g-dev make
RUN version=3.8.7 && \
    wget https://www.python.org/ftp/python/$version/Python-$version.tgz && \
    tar -xf Python-$version.tgz && \
    cd Python-$version && \
    ./configure && \
    make -j $(nproc) && \
    make install && \
    cd .. && \
    rm -r Python-$version*

RUN filename=commandlinetools-linux-6609375_latest.zip && \
    wget https://dl.google.com/android/repository/$filename && \
    mkdir -p android-sdk/cmdline-tools && \
    unzip -q -d android-sdk/cmdline-tools $filename && \
    rm $filename
