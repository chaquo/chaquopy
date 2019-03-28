# The toolchain and libcrystax builds require a large build context and take several minutes
# even if Docker ultimately decides to use its cache, so we keep them in a separate Dockerfile,
# and exclude them from this context using .dockerignore.
FROM chaquopy-crystax

RUN rm -r src/crystax/platform/ndk/build/tools
COPY crystax/platform/ndk/build/tools/prebuilt-common.sh \
     crystax/platform/ndk/build/tools/ndk-common.sh \
     crystax/platform/ndk/build/tools/dev-defaults.sh \
     src/crystax/platform/ndk/build/tools/

RUN apt-get update && \
    apt-get install -y perl-modules
COPY openssl src/openssl
COPY crystax/platform/ndk/build/tools/build-target-openssl.sh \
     src/crystax/platform/ndk/build/tools/
COPY crystax/platform/ndk/sources/openssl src/crystax/platform/ndk/sources/openssl
RUN src/crystax/platform/ndk/build/tools/build-target-openssl.sh \
        --verbose --ndk-dir=$(pwd)/crystax --abis=$abis src/openssl && \
    rm -r /tmp/ndk-*

# Python 3.6 isn't included in this version of Debian, so use a third-party build.
RUN apt-get update && \
    apt-get install -y patch && \
    wget https://github.com/chriskuehl/python3.6-debian-stretch/releases/download/v3.6.3-1-deb9u1/{python3.6,python3.6-minimal,libpython3.6,libpython3.6-minimal,libpython3.6-stdlib}_3.6.3-1.deb9u1_amd64.deb && \
    apt install -y ./*.deb && \
    rm *.deb

COPY python src/python
COPY crystax/platform/ndk/build/tools/build-target-python.sh \
     src/crystax/platform/ndk/build/tools/
COPY crystax/platform/ndk/build/tools/build-target-python \
     src/crystax/platform/ndk/build/tools/build-target-python
RUN src/crystax/platform/ndk/build/tools/build-target-python.sh \
        --verbose --ndk-dir=$(pwd)/crystax --abis=$abis src/python && \
    rm -r /tmp/ndk-*
