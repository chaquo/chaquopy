# Release procedure


## Gradle plugin

Run gradlew -P cmakeBuildType=Release :gradle-plugin:check

Copy gradle-plugin/build/libs/gradle.jar to the Maven repository under the name
com/chaquo/python/gradle/<version>/gradle-<version>.jar.

Run server/maven/update_checksums.sh. (TODO: My Gradle client uses HTTP HEAD to detect changes
and never looks at checksums; if everybody else is the same, we might as well remove them.)


## Demo app

Run "demo/update_public.sh <since-commit>", where <since-commit> is the commit (in this
repository) from which the public repository was last updated. If the script reports any files
which require manual merging (e.g. build.gradle), examine them and update the public repository
as necessary.

Update version number in public/demo/build.gradle, adjusting SDK version number if necessary.

"Generate Signed APK" in Android Studio, and test all features on emulator and phone.

Upload APK to Google Play. Update description and screenshots if necessary.

Upload APK to Maven repository.


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
