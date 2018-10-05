# The toolchain and libcrystax builds require a large build context and take several minutes
# even if Docker ultimately decides to use its cache, so we keep them in a separate Dockerfile,
# and exclude them from this context using .dockerignore.
FROM chaquopy-crystax

COPY crystax/platform/ndk src/crystax/platform/ndk

# OpenSSL
COPY openssl src/openssl
RUN rm -r crystax/sources/openssl && \
    src/crystax/platform/ndk/build/tools/build-target-openssl.sh \
        --verbose --ndk-dir=$(pwd)/crystax --abis=$ABIS src/openssl && \
    rm -r /tmp/ndk-

# The Crystax Python build script runs `configure` with environment variables pointing to the
# GCC 4.9 toolchain, but then ndk-build uses GCC 5. This is probably unintentional, but we know
# it works so we might as well leave it alone until we remove Crystax entirely.

RUN rm -r crystax/sources/python

# Python 2.7
COPY python2.7 src/python2.7
RUN apt-get update && \
    apt-get install -y python2.7 && \
    src/crystax/platform/ndk/build/tools/build-target-python.sh \
        --verbose --ndk-dir=$(pwd)/crystax --abis=$ABIS src/python2.7 && \
    rm -r /tmp/ndk-

# Python 3.6
COPY python src/python
RUN apt-get update && \
    apt-get install -y libmpdec2 patch && \
    wget --progress=dot:giga https://github.com/chriskuehl/python3.6-debian-stretch/releases/download/v3.6.3-1-deb9u1/{python3.6,python3.6-minimal,libpython3.6-minimal,libpython3.6-stdlib}_3.6.3-1.deb9u1_amd64.deb && \
    dpkg -i *.deb && \
    rm *.deb && \
    src/crystax/platform/ndk/build/tools/build-target-python.sh \
        --verbose --ndk-dir=$(pwd)/crystax --abis=$ABIS src/python && \
    rm -r /tmp/ndk-

RUN rm -r src