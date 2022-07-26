FROM chaquopy-base

# Indicate that we accept the Android SDK license. The platform version here isn't critical:
# all versions have the same license, and if the app requires a different version, the build
# process will automatically download it.
RUN yes | android-sdk/cmdline-tools/tools/bin/sdkmanager "platforms;android-31"

COPY maven maven
COPY server/pypi/dist server/pypi/dist
COPY VERSION.txt ./
