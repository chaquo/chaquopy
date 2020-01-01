# Running this image generates the Chaquopy Maven repository in the directory /root/maven. This
# can be a mount or a volume if you wish, or you can just copy it out of the container using
# `docker cp`.

FROM chaquopy-target

RUN apt-get update && \
    apt-get install -y python3-pip

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

RUN yes | android-sdk/tools/bin/sdkmanager 'cmake;3.6.4111459'

COPY product/buildSrc product/buildSrc
RUN platform_ver=$(grep COMPILE_SDK_VERSION \
                   product/buildSrc/src/main/java/com/chaquo/python/Common.java \
                   | sed 's|.* = \(.*\);.*|\1|'); \
    yes | android-sdk/tools/bin/sdkmanager "platforms;android-$platform_ver"

COPY product/runtime/requirements-build.txt product/runtime/
RUN pip3 install -r product/runtime/requirements-build.txt

COPY product/build.gradle product/gradlew product/settings.gradle product/
COPY product/gradle product/gradle
COPY product/gradle-plugin product/gradle-plugin
COPY product/runtime product/runtime
COPY server/license/check_ticket.py server/license/

# Leave empty for default license enforcement.
# `free` for no license enforcement at all.
# `ec` for Electron Cash.
ARG license_mode

RUN (echo sdk.dir=$(pwd)/android-sdk && \
     echo ndk.dir=$(pwd)/android-ndk && \
     echo chaquopy.license_mode=$license_mode) > product/local.properties

COPY VERSION.txt ./

# Options: Debug, Release
ARG build_type=Release

RUN product/gradlew -p product -P cmakeBuildType=$build_type \
    gradle-plugin:publish runtime:publish

RUN apt-get update && \
    apt-get install -y zip
COPY docker-entrypoint.sh .
COPY target/package-target.sh target/
ENTRYPOINT ["./docker-entrypoint.sh"]