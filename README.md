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

Update version number in public/demo/build.gradle, adjusting SDK version number if necessary.

"Generate Signed APK" in Android Studio, and test on emulator and phone.

Upload APK to Google Play and to Maven repository.


## Documentation

Update public/demo/CHANGELOG.md for demo app changes, and add date.

Update runtime/docs/sphinx/changelog.rst for product changes, and add date.

If sphinx or javadoc have changed:

* Update runtime/docs/sphinx/changelog.rst for product changes, and add date.
* Adjust VERSION.txt temporarily if that version isn't released yet.
* Build and upload to server. If major.minor version number has changed, update "current"
  symlink and add link on WordPress documentation page.

Post blog entry on website.


## Source control

Commit public/demo repository, and push to chaquo.com and GitHub.

Commit python repository, add version number tag, and push. Then increment
python/VERSION.txt for next version number.
