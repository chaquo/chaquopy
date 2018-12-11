# This image must be built in the context of the repository root.

FROM chaquopy-app
ENV app_dir="server/pypi/pkgtest"

COPY demo demo
COPY server/pypi/packages server/pypi/packages
COPY $app_dir $app_dir

RUN echo "sdk.dir=$(pwd)/android-sdk" > $app_dir/local.properties
RUN cd $app_dir && ./gradlew app:assembleDebug
