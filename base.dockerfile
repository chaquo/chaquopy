# Base image shared between chaquopy-target and chaquopy-app

FROM debian:bullseye-20191224
SHELL ["/bin/bash", "-c"]
WORKDIR /root

RUN apt-get update && \
    apt-get install -y unzip wget
RUN echo "progress=dot:giga" > .wgetrc

RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    ln -sf python3 /usr/bin/python

# The current version of sdkmanager doesn't work with Java 9 or later
# (https://stackoverflow.com/a/53619947), so install an Oracle Java 8 build instead
# (https://stackoverflow.com/a/10959815). A fix for this is planned to be released with Android
# Studio 3.6 (https://issuetracker.google.com/issues/67495440#comment20).
RUN wget -c --header "Cookie: oraclelicense=accept-securebackup-cookie" \
http://download.oracle.com/otn-pub/java/jdk/8u131-b11/d54c1d3a095b4ff2b6607d096fa80163/jdk-8u131-linux-x64.tar.gz && \
    tar -xf jdk*.tar.gz && \
    ( for name in java javac; do ln -s $(pwd)/jdk*/bin/$name /usr/bin/$name; done ) && \
    rm jdk*.tar.gz

RUN filename=sdk-tools-linux-4333796.zip && \
    wget https://dl.google.com/android/repository/$filename && \
    mkdir android-sdk && \
    unzip -q -d android-sdk $filename && \
    rm $filename
