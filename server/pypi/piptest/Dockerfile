FROM chaquopy-app

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
