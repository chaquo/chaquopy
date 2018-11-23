FROM chaquopy-target

RUN apt-get update && \
    apt-get install -y openjdk-8-jdk-headless

RUN filename=sdk-tools-linux-4333796.zip && \
    wget https://dl.google.com/android/repository/$filename && \
    mkdir android-sdk && \
    unzip -q -d android-sdk $filename && \
    rm $filename

# Indicate that we accept the license which has the given hash.
RUN mkdir android-sdk/licenses && \
    echo d56f5187479451eabf01fb78af6dfcb131a6481e > android-sdk/licenses/android-sdk-license

COPY maven maven
COPY server/pypi/dist server/pypi/dist
COPY VERSION.txt ./
