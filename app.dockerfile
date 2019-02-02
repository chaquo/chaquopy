FROM debian:stretch-20180831
SHELL ["/bin/bash", "-c"]
WORKDIR /root

RUN apt-get update && \
    apt-get install -y openjdk-8-jdk-headless python3 unzip wget
RUN echo "progress=dot:giga" > .wgetrc

RUN filename=sdk-tools-linux-4333796.zip && \
    wget https://dl.google.com/android/repository/$filename && \
    mkdir android-sdk && \
    unzip -q -d android-sdk $filename && \
    rm $filename

# Indicate that we accept the Android SDK license. The platform version here doesn't matter:
# all versions require the same license, and if the app build.gradle specifies a different
# version, the build process will automatically download it.
RUN yes | android-sdk/tools/bin/sdkmanager "platforms;android-28"

COPY maven maven
COPY server/pypi/dist server/pypi/dist
COPY VERSION.txt ./
