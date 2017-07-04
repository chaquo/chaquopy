# Release procedure


## Gradle plugin

Run gradlew -P testPythonArgs="discover -v" -P cmakeBuildType=Release :gradle-plugin:testIntegration

Copy gradle-plugin/build/libs/gradle.jar to the Maven repository under the name
com/chaquo/python/gradle/<version>/gradle-<version>.jar.

Run server/maven/update_checksums.sh. (TODO: My Gradle client uses HTTP HEAD to detect changes
and never looks at checksums; if everybody else is the same, we might as well remove them.)


## Demo app

Copy updates in demo to public/demo.

Copy updates in runtime/src/test to public/demo/app/src/main.

Update version number in public/demo/build.gradle, and build release APK in Android Studio.
Test on emulator and phone.

Upload APK to Google Play and to Maven repository.


## Documentation

Update runtime/docs/sphinx/changelog.rst for product changes, and add date.

Update public/demo/CHANGELOG.md for demo app changes, and add date.

Build sphinx and javadoc. Upload to server, updating "current" symlink and adding link to documentation page.

Post blog entry on website.


## Source control

Commit public/demo repository, and push to chaquo.com and GitHub.

Commit python repository, add version number tag, and push. Then increment
python/VERSION.txt for next version number.
