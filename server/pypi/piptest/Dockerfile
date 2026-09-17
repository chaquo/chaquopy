FROM debian:trixie

WORKDIR /root

RUN apt-get update && \
    apt-get -y install openjdk-21-jdk-headless unzip wget

# Install Android SDK
ENV ANDROID_HOME=/root/android-sdk
RUN filename=commandlinetools-linux-6609375_latest.zip && \
    wget https://dl.google.com/android/repository/$filename && \
    mkdir -p $ANDROID_HOME/cmdline-tools && \
    unzip -q -d $ANDROID_HOME/cmdline-tools $filename && \
    rm $filename

# Install Gradle
ENV piptest=/root/server/pypi/piptest
COPY src/gradlew $piptest/src/
COPY src/gradle $piptest/src/gradle/
RUN cd $piptest/src && ./gradlew

# Install Python
RUN filename="Miniconda3-latest-Linux-$(uname -m).sh" && \
    wget https://repo.anaconda.com/miniconda/$filename && \
    bash $filename -b -p ~/miniconda3 && \
    rm $filename
COPY src/app/build.gradle $piptest/src/app/
RUN python_version=$( \
        grep "version =" $piptest/src/app/build.gradle | \
        sed -E 's/.*([0-9]+\.[0-9]+).*/\1/' \
    ) && \
    CI=1 ~/miniconda3/condabin/conda create -n piptest python=$python_version && \
    ln -s ~/miniconda3/envs/piptest/bin/python* /usr/local/bin

# Fill caches by doing an initial run
COPY piptest.py $piptest/
COPY src $piptest/src/
RUN $piptest/piptest.py six

ENV LC_ALL="C.UTF-8"
ENTRYPOINT ["server/pypi/piptest/piptest.py"]
