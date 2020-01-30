FROM chaquopy-base

# Indicate that we accept the Android SDK license. The platform version here doesn't matter:
# all versions require the same license, and if the app build.gradle specifies a different
# version, the build process will automatically download it.
RUN yes | android-sdk/tools/bin/sdkmanager "platforms;android-28"

RUN apt-get update && \
    apt-get install -y python3.8 && \
    ln -sf python3.8 /usr/bin/python3

COPY maven maven
COPY server/pypi/dist server/pypi/dist
COPY VERSION.txt ./
