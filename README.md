# Release procedure

## Gradle plugin

Run gradlew -P cmakeBuildType=Release :gradle-plugin:test-integration

Copy gradle-plugin/build/libs/gradle.jar to the Maven repository under the name
com/chaquo/python/gradle/<version>/gradle-<version>.jar.

Run server/maven/update_checksums.sh.

## Demo app

Copy updates in demo to public/demo.

Copy updates in runtime/src/test to public/demo/app/src/main.

Update version number in public/demo/build.gradle.

Build release APK in Android Studio, test on emulator and phone.

Commit public/demo repository, and push to chaquo.com and GitHub.

Add version number tag to python repository, and push to chaquo.com. Then increment
python/VERSION.txt for next version number.

Upload APK to Google Play.
