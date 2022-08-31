FROM debian:buster

# target, maven and product must be passed in as volumes.
WORKDIR /root/target

# Pyenv and its supporting packages
# (https://github.com/pyenv/pyenv/wiki#suggested-build-environment).
RUN apt-get update && \
    apt-get -y install curl git make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev \
    xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
RUN curl https://pyenv.run | PYENV_GIT_TAG=v2.3.3 bash

# Install all Python versions. We need to include every minor version that we support,
# but the micro version doesn't matter.
RUN apt-get update && \
    apt-get -y install python3.7
RUN ~/.pyenv/bin/pyenv install 3.8.13
RUN ~/.pyenv/bin/pyenv install 3.9.13
RUN ~/.pyenv/bin/pyenv global 3.8.13 3.9.13 && \
    ln -sf ~/.pyenv/shims/python*.* /usr/local/bin

# Build tools
RUN apt-get update && \
    apt-get -y install \
    # Download
    curl wget \
    # Packaging
    unzip zip \
    # Build
    automake autopoint libtool-bin make patchelf \
    # OpenSSL
    perl \
    # sdkmanager
    openjdk-11-jdk-headless \
    # make_standalone_toolchain.py
    python \
    # Fortran
    bison flex g++

# This must be passed in as a volume.
ENV ANDROID_HOME=/root/android-sdk

# If you want to run a different script, simply pass it to `docker run`.
CMD ./build-all.sh
