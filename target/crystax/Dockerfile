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
        --verbose --systems=linux-x86_64 --arch=arm,arm64,x86,x86_64 \
        src/crystax/toolchain && \
    rm -r /tmp/ndk-* && \
    mv src/crystax/platform/ndk/toolchains crystax

ENV abis="armeabi-v7a,arm64-v8a,x86,x86_64"

# Rebuild libcrystax to fix various bugs (see commit history of `crystax/platform/ndk`).
#
# armeabi and armeabi-v7a-hard are both required by make-standalone-toolchain.sh. Also,
# armeabi is required for OpenBLAS: see pypi/packages/chaquopy-openblas/build.sh.
#
# We build one ABI at a time because it fails for some reason when both x86 and x86_64 are
# requested. Specifically, we get these warnings for every i386 source file:
#
#     GNUmakefile:617: warning: overriding recipe for target
#     '/root/src/crystax/platform/ndk/sources/crystax/obj/i386/gen/freebsd/lib/msun/src/s_nextafter.c.o'
#     GNUmakefile:617: warning: ignoring old recipe for target
#     '/root/src/crystax/platform/ndk/sources/crystax/obj/i386/gen/freebsd/lib/msun/src/s_nextafter.c.o'
#
# And then the command `LD x86 [i386] libcrystax.so` fails with a number of undefined
# references, all of which are signal-related (e.g. sigfillset, sigdelset, signalfd), with the
# exception of `wait4`.
RUN for abi in $(echo $abis,armeabi,armeabi-v7a-hard | sed 's/,/ /g'); do \
        NDK=$(pwd)/crystax \
        ABIS=$abi \
        make -j $(nproc) -C src/crystax/platform/ndk/sources/crystax || exit 1; \
    done && \
    mv src/crystax/platform/ndk/sources/crystax crystax/sources
