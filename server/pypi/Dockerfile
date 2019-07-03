# This image takes the same command-line arguments as build-wheel.py, except for `--ndk`, which
# should be omitted.
#
# Each run will generate one wheel file in the directory /root/pypi/dist, which is structured
# as a PyPI respository. If a package requires other packages to build against, then this
# directory must be supplied as a mount or a volume which already contains those packages'
# wheel files.

FROM chaquopy-target

# OpenCV requires Python 2 even when building for Python 3: see its patch.
RUN apt-get update && \
    apt-get -y install python && \
    ln -sf python3.6 /usr/bin/python

RUN wget -q -O - https://bootstrap.pypa.io/get-pip.py | python3.6

# Miscellaneous build tools
#
# The Python `-dev` packages are required for some packages (e.g. OpenCV and TensorFlow) which
# need to build things for the host Python.
RUN apt-get update && \
    apt-get -y install autoconf cmake git make patch && \
    wget https://github.com/chriskuehl/python3.6-debian-stretch/releases/download/v3.6.3-1-deb9u1/{python3.6-dev,libpython3.6-dev}_3.6.3-1.deb9u1_amd64.deb && \
    apt install -y ./*.deb && \
    rm *.deb && \
    ln -sf python3.6 /usr/bin/python && \
    ln -sf python3.6 /usr/bin/python3

# Bazel (for TensorFlow)
RUN apt-get update && \
    apt-get -y install pkg-config zip g++ zlib1g-dev unzip && \
    version=0.16.1 && \
    filename=bazel-$version-installer-linux-x86_64.sh && \
    wget https://github.com/bazelbuild/bazel/releases/download/$version/$filename && \
    chmod +x $filename && \
    ./$filename && \
    rm $filename

# patchelf (see comment in packages/chaquopy-libgfortran/build.sh)
RUN commit=6bfcafbba8d89e44f9ac9582493b4f27d9d8c369 && \
    wget -q -O - https://github.com/NixOS/patchelf/archive/$commit.tar.gz | tar -xzf - && \
    ( cd patchelf-$commit && ./bootstrap.sh && ./configure && make && make install ) && \
    rm -r patchelf-$commit

COPY requirements.txt pypi/
RUN pip3.6 install -r pypi/requirements.txt

COPY . pypi/

ENV LC_ALL="C.UTF-8"
ENTRYPOINT ["python3.6", "pypi/build-wheel.py", "--ndk", "crystax"]
