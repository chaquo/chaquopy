# Running this image generates the Chaquopy Maven repository in the directory /root/maven. This
# can be a mount or a volume if you wish, or you can just copy it out of the container using
# `docker cp`.

FROM chaquopy-target

RUN apt-get update && \
    apt-get install -y openjdk-8-jdk-headless
RUN wget -q -O - https://bootstrap.pypa.io/get-pip.py | python3.6

RUN filename=sdk-tools-linux-4333796.zip && \
    wget https://dl.google.com/android/repository/$filename && \
    mkdir android-sdk && \
    unzip -q -d android-sdk $filename && \
    rm $filename

RUN yes | android-sdk/tools/bin/sdkmanager 'cmake;3.6.4111459'

# Not installing the NDK with sdkmanager, because there's no way to select a specific version
# to make the build reproducible.
#
# NDK r18 increased the minimum API level to 16: our minimum is currently 15.
RUN filename=android-ndk-r17c-linux-x86_64.zip && \
    wget https://dl.google.com/android/repository/$filename && \
    unzip -q $filename && \
    rm $filename && \
    mv android-ndk-r17c android-ndk

COPY product/buildSrc product/buildSrc
RUN platform_ver=$(grep COMPILE_SDK_VERSION \
                   product/buildSrc/src/main/java/com/chaquo/python/Common.java \
                   | sed 's|.* = \(.*\);.*|\1|'); \
    yes | android-sdk/tools/bin/sdkmanager "platforms;android-$platform_ver"

COPY product/runtime/requirements-build.txt product/runtime/
RUN pip install -r product/runtime/requirements-build.txt

COPY product/build.gradle product/gradlew product/settings.gradle product/
COPY product/gradle product/gradle
COPY product/gradle-plugin product/gradle-plugin
COPY product/runtime product/runtime

# Leave empty for default license enforcement.
# `free` for no license enforcement at all.
# `ec` for Electron Cash.
ARG license_mode

RUN (echo sdk.dir=$(pwd)/android-sdk && \
     echo ndk.dir=$(pwd)/android-ndk && \
     echo crystax.dir=$(pwd)/crystax && \
     echo chaquopy.license_mode=$license_mode) > product/local.properties

COPY VERSION.txt ./

# Options: Debug, Release
ARG build_type=Release

RUN product/gradlew -p product -P cmakeBuildType=$build_type \
    gradle-plugin:assemble gradle-plugin:writePom

COPY docker-entrypoint.sh .
COPY target/package-target.sh target/
ENTRYPOINT ["./docker-entrypoint.sh"]