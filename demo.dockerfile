FROM chaquopy-app

COPY product/runtime/src/test product/runtime/src/test
COPY demo demo

RUN echo "sdk.dir=$(pwd)/android-sdk" > demo/local.properties
RUN demo/gradlew -p demo app:assembleDebug
