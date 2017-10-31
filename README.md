# Development environment setup

(NOTE: This procedure has not been fully tested and may be incomplete.)

Install the following prerequisites:

* Java 8 or later, either on the PATH as "java", or pointed to by JAVA_HOME.
* Python 2.7 on the PATH as "python2".
* Android SDK, including the following packages:
   * Build Tools
   * CMake
   * NDK
   * SDK Platform version corresponding to MIN_SDK_VERSION in
     product/buildSrc/src/main/java/com/chaquo/python/Common.java.
* Crystax NDK (for Python header files)

Create product/local.properties with the properties listed in product/runtime/build.gradle.


# Release procedure

## Sanity check

Test demo app on emulator and phone.


## Gradle plugin

Run `gradlew -P cmakeBuildType=Release :gradle-plugin:check` on all supported workstation OSs.

Copy gradle-plugin/build/libs/gradle.jar to local and remote Maven repository.


## Demo app

Run "demo/update_public.sh <since-commit>", where <since-commit> is the commit or label in
*this* repository from which the public repository was last updated. If the script reports any
files which require manual merging (e.g. build.gradle), examine them and update the public
repository as necessary. (If the script reports *every* file, this is probably because of
end-of-line issues: run it a second time and it should give the correct output.)

Update version number in public/demo/build.gradle, adjusting SDK version number if necessary.

"Generate Signed APK" in Android Studio, and test all features on minimum-version emulator,
up-to-date emulator, and phone.

Upload APK to Google Play. Update description and screenshots if necessary.

Copy APK to local and remote Maven repository.


## Documentation

Update public/demo/CHANGELOG.md for demo app changes, and runtime/docs/sphinx/changelog.rst for
SDK changes.

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
