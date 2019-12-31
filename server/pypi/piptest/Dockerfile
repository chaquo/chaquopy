FROM chaquopy-app

# Python 3.6 isn't included in this version of Debian, so use a third-party build.
RUN apt-get update && \
    apt-get install -y patch && \
    wget https://github.com/chriskuehl/python3.6-debian-stretch/releases/download/v3.6.3-1-deb9u1/{python3.6,python3.6-dev,python3.6-minimal,libpython3.6,libpython3.6-dev,libpython3.6-minimal,libpython3.6-stdlib}_3.6.3-1.deb9u1_amd64.deb && \
    apt install -y ./*.deb && \
    rm *.deb

# Pre-install Gradle and other build components so they're not downloaded on every run.
ENV piptest=/root/server/pypi/piptest
COPY src $piptest/src
RUN echo "sdk.dir=$(pwd)/android-sdk" > $piptest/src/local.properties
RUN tmp_dir=$piptest/build/tmp && \
    mkdir -p $tmp_dir && \
    cp -a $piptest/src/* $tmp_dir && \
    cd $tmp_dir && \
    piptest_verbose=False piptest_package=six ./gradlew app:preBuild && \
    rm -r $tmp_dir

COPY piptest.py server/pypi/piptest/
ENV LC_ALL="C.UTF-8"
ENTRYPOINT ["server/pypi/piptest/piptest.py"]
