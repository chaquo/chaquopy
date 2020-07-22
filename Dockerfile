# Running this image generates the Chaquopy Maven repository in the directory /root/maven. This
# can be a mount or a volume if you wish, or you can just copy it out of the container using
# `docker cp`.

FROM chaquopy-target

COPY product/buildSrc product/buildSrc
RUN platform_ver=$(grep COMPILE_SDK_VERSION \
                   product/buildSrc/src/main/java/com/chaquo/python/Common.java \
                   | sed 's|.* = \(.*\);.*|\1|'); \
    yes | android-sdk/cmdline-tools/tools/bin/sdkmanager \
        "cmake;3.6.4111459" "platforms;android-$platform_ver"

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
     echo -n ndk.dir= && \
     echo $(pwd)/android-sdk/ndk/* && \
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