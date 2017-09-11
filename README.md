# Release procedure


## Gradle plugin

Run gradlew -P cmakeBuildType=Release :gradle-plugin:check

Copy gradle-plugin/build/libs/gradle.jar to the Maven repository under the name
com/chaquo/python/gradle/<version>/gradle-<version>.jar.

Run server/maven/update_checksums.sh. (TODO: My Gradle client uses HTTP HEAD to detect changes
and never looks at checksums; if everybody else is the same, we might as well remove them.)


## Demo app

Delete public/demo/app/src/main and replace with copy from demo/app/src/main.
copied from runtime/src/test).

Merge product/runtime/src/test/{java,python} into the corresponding directories under
public/demo/app/src/main.

Copy updates in all other files under python/demo (some will have to be manually merged).

Update version number in public/demo/build.gradle, adjusting SDK version number if necessary.

"Generate Signed APK" in Android Studio, and test all features on emulator and phone.

Upload APK to Google Play and to Maven repository.


## Documentation

Update public/demo/CHANGELOG.md for demo app changes, and add date.

Update runtime/docs/sphinx/changelog.rst for product changes, and add date.

If sphinx or javadoc have changed:

* Adjust VERSION.txt temporarily if that version isn't released yet.
* Build and upload to server.
* If major.minor version number has changed, update "current" symlink and add link on WordPress
  documentation page.

Post blog entry on website.


## Source control

Commit public/demo repository, and push to chaquo.com and GitHub.

Commit python repository, add version number tag, and push. Then increment
python/VERSION.txt for next version number.
