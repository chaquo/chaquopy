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
RUN apt-get update && \
    apt-get -y install autoconf cmake git patch

# Bazel (for TensorFlow)
RUN apt-get update && \
    apt-get -y install pkg-config zip g++ zlib1g-dev unzip && \
    version=0.16.1 && \
    filename=bazel-$version-installer-linux-x86_64.sh && \
    wget https://github.com/bazelbuild/bazel/releases/download/$version/$filename && \
    chmod +x $filename && \
    ./$filename && \
    rm $filename

COPY requirements.txt pypi/
RUN pip3.6 install -r pypi/requirements.txt

COPY . pypi/
ENV LC_ALL="C.UTF-8"
ENTRYPOINT ["pypi/docker-entrypoint.sh"]
