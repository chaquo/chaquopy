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

## Pre-release tests

Test demo app (any device, any Python version: other combinations will be covered below).

Test pkgtest app on emulator and phone for both Python 2 and 3.


## Gradle plugin

Run `gradlew -P cmakeBuildType=Release gradle-plugin:check`. While the tests are running, copy
the generated .jar to other supported workstation OSs and do the same there.

Run `gradlew gradle-plugin:writePom`.

Copy .jar and .pom from gradle-plugin/build/libs to Maven repository.


## Demo app

Update version numbers in public/demo/build.gradle and public/demo/app/build.gradle.

Run "demo/update_public.sh <since-commit>", where <since-commit> is the commit or label in
*this* repository from which the public repository was last updated. If the script reports any
files which require manual merging (e.g. build.gradle), examine them and update the public
repository as necessary. (If the script lists too many files, this is probably because of
end-of-line issues: run it a second time and it should give the correct output.)

"Generate Signed APK" in Android Studio for Python 2 and 3, and test all features on:

* minSdkVersion emulator
* targetSdkVersion emulator
* Phone

Release APKs on Google Play. Update public/demo/CHANGELOG.md for demo app changes, and
runtime/docs/sphinx/changelog.rst for SDK changes, and copy these into the Google Play release
notes. Update description and screenshots if necessary.

Copy APKs to Maven repository.


## Documentation

If sphinx or javadoc have changed:

* Adjust VERSION.txt temporarily if rebuilding docs for an old version.
* Build and upload to server.
* If major.minor version number has changed, update "current" symlink and add link on WordPress
  documentation page.

Post blog entry to website and Facebook.

Update GitHub issues if necessary.


## Source control

Commit public/demo repository, and push to chaquo.com and GitHub.

Commit python repository, add version number tag, and push. Then increment
python/VERSION.txt for next version number.
