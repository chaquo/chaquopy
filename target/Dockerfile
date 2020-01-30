FROM chaquopy-base

# When moving to a new version of the NDK, carefully review the following:
# * The release notes (https://developer.android.com/ndk/downloads/revision_history)
# * https://android.googlesource.com/platform/ndk/+/ndk-release-rXX/docs/BuildSystemMaintainers.md,
#   where XX is the NDK version. Check over the `master` version of that document as well.
RUN yes | android-sdk/tools/bin/sdkmanager "ndk;18.1.5063045"

COPY build-toolchains.sh build-toolchain.sh build-common.sh target/
RUN target/build-toolchains.sh android-sdk/ndk/* "arm64-v8a armeabi-v7a x86 x86_64"
COPY for-each-abi.sh target/

# Fortran compiler (for OpenBLAS and SciPy). Although this is only required by the pypi
# Dockerfile, we put it here so we don't have to rebuild it every time we change the versions
# of any of the things below.
RUN apt-get update && \
    apt-get -y install bison flex g++ make
COPY gcc target/gcc
RUN cd target/gcc/gcc-4.9 && contrib/download_prerequisites
COPY build-fortran.sh target/
RUN target/for-each-abi.sh target/build-fortran.sh

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

# bzip2
COPY build-bzip2.sh target
RUN target/for-each-abi.sh target/build-bzip2.sh

# xz (for lzma module)
COPY build-xz.sh target
RUN target/for-each-abi.sh target/build-xz.sh

# Python
RUN apt-get update && \
    apt-get install -y python3.8
COPY python target/python
COPY build-python.sh target/
RUN target/for-each-abi.sh target/build-python.sh
