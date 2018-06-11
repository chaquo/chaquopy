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

## Runtime

Run `gradlew runtime:check`.


## Gradle plugin

Free up RAM if necessary. If restarting Android Studio, do it before starting the tests, as
this may kill the Gradle daemon.

On each supported workstation OS, run the following tasks with `gradlew -P
cmakeBuildType=Release`:
* `gradle-plugin:testPython`
* `gradle-plugin:testIntegration-X.Y` for each supported Android Studio version.

Remove any license key from pkgtest app, then test it for both Python 2 and 3 on the following
devices, with at least one app on each device being a clean install:
* API 18 emulator (earlier versions give "too many libraries" error (#5316)).
* targetSdkVersion emulator
* Any ARM device

On one of these devices, test on both Python 2 and 3 that the license notification and enforcement
works correctly.


## Demo apps

Run `gradlew gradle-plugin:writePom`.

Copy .jar and .pom from gradle-plugin/build/libs to Maven repository.

Run "demo/update_public.sh <since-commit>", where <since-commit> is the commit or label in
*this* repository from which the public repository was last updated. If the script reports any
files which require manual copying or merging (e.g. build.gradle), examine them and update the
public repository as necessary.

Update version numbers in public/demo/build.gradle and public/demo/app/build.gradle.

"Clean Project", then "Generate Signed APK" for both Python 2 and 3, and test all features on the
following devices, with at least one app on each device being a clean install:
* minSdkVersion emulator
* targetSdkVersion emulator
* Any ARM device

Update public/demo/CHANGELOG.md for demo app changes, and runtime/docs/sphinx/changelog.rst for
SDK changes.

Release apps on Google Play, updating description and screenshots if necessary.

Copy APKs to Maven repository.


## Documentation

If sphinx or javadoc have changed:

* Adjust VERSION.txt temporarily if rebuilding docs for an old version.
* Build and upload to server.
* If major.minor version number has changed:
  * Update "current" symlink.
  * Add link on WordPress documentation page.


## Source control

Commit public/demo repository, and push to chaquo.com and GitHub.

If this release includes important changes, update public/console and public/hello, and push
them as well.

Commit python repository, add version number tag, and push.

Increment python/VERSION.txt for next version number.


## User communication

Post blog entry to website and Facebook.

Update any GitHub issues.

Email any affected users, including those who gave a thumbs up to an issue but didn't comment.
