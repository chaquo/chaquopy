# Release procedure


## Demo app

Copy updates in demo to public/demo.

Copy updates in runtime/src/test to public/demo/app/src/main.

Update version number in public/demo/build.gradle, and build release APK in Android Studio.
Test on emulator and phone.

Upload APK to Google Play.


## Gradle plugin

Run gradlew -P cmakeBuildType=Release :gradle-plugin:test-integration

Copy gradle-plugin/build/libs/gradle.jar to the Maven repository under the name
com/chaquo/python/gradle/<version>/gradle-<version>.jar.

Run server/maven/update_checksums.sh. (TODO: My Gradle client uses HTTP HEAD to detect changes
and never looks at checksums; if everybody else is the same, we might as well remove them.)


## Documentation

Build sphinx and javadoc. Upload to server, updating "current" symlink and adding link to documentation page.

Update public/demo/CHANGELOG.md.

Post blog entry on website.


## Source control

Commit public/demo repository, and push to chaquo.com and GitHub.

Commit python repository if necessary. Add version number tag, and push. Then increment
python/VERSION.txt for next version number.
