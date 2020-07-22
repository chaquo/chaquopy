FROM debian:bullseye-20200607
SHELL ["/bin/bash", "-c"]
WORKDIR /root

RUN apt-get update && \
    apt-get install -y unzip wget
RUN echo "progress=dot:giga" > .wgetrc

RUN apt-get update && \
    apt-get install -y python3 python3-dev python3-pip && \
    ln -sf python3 /usr/bin/python

RUN apt-get update && \
    apt-get install -y default-jdk-headless

RUN filename=commandlinetools-linux-6609375_latest.zip && \
    wget https://dl.google.com/android/repository/$filename && \
    mkdir -p android-sdk/cmdline-tools && \
    unzip -q -d android-sdk/cmdline-tools $filename && \
    rm $filename
