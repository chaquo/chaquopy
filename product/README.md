# Introduction

This file contains instructions for building and testing Chaquopy.


# Build prerequisites

* A local Python installation for each Python major.minor version suported by Chaquopy
  (list them with `target/list-versions.py --minor`). These must be on the PATH as
  `pythonX.Y` on Unix, or `py -X.Y` on Windows.
  * On Linux, install them from your distribution, or use Miniconda.
  * On Mac and Windows, download them from https://python.org/.

* Android Python headers and libraries in target/prefix. These can be installed as
  shown in ci.yml.

* Python requirements from runtime/requirements-build.txt. In particular, `cython` must be
  on the PATH.

* Android SDK. Set the `ANDROID_HOME` environment variable to point at its location, and
  install the following packages:
   * CMake: version from `sdkCmakeDir` in runtime/build.gradle.
   * NDK (side by side): version from `ndkDir` in runtime/build.gradle.
   * SDK Platform: version from `COMPILE_SDK_VERSION` in
     buildSrc/src/main/java/com/chaquo/python/internal/Common.java.

* JDK version 8. Create a `local.properties` file in `product` (i.e. the same directory
  as this README), setting the JDK location as follows:

      chaquopy.java.home.8=<path>


# Build

The build can be done either at the command line using `gradlew`, or by opening the project in
Android Studio or IntelliJ.

The top-level Gradle tasks are as follows:

* `gradle-plugin:publish` for the `com.chaquo.python:gradle` artifact.
* `runtime:publish` for the `com.chaquo.python.runtime` artifacts. For a release build, add `-P
  cmakeBuildType=Release` to the Gradle command line.

All artifacts are generated in the `maven` directory in the root of this Git repository, and
all apps in the repository are set to give that directory higher priority than the public Maven
server.


# Runtime tests

The runtime unit tests are mainly run on Android via the demo app in ../demo. However,
the non-Android-specific features, such as the Java/Python interface, can also be tested
directly on the build platform.

Prerequisities (on Windows, these must be the MSYS2 versions):

* GCC and binutils.

* The same Python major.minor version as Chaquopy uses by default.

  * On Linux, install it from your distribution, or use Miniconda. Make sure you also
    include the development headers (e.g. `pythonX.Y-dev` on Debian).

  * On Mac, download it from https://python.org/.

  * On Windows, install it using MSYS2's `pacman`. If MSYS2 has already moved on to a
    later Python version, download the correct version from
    http://repo.msys2.org/mingw/mingw64/ and install it with `pacman -U`.

    Make sure your PATH is set so that invocations of `pythonX.Y` will use the MSYS2
    version.

The tests are run by the Gradle tasks `runtime:testPython` and `runtime:testJava`. Or run
`runtime:check` to test everything at once.


# Gradle plugin tests

There are a few Gradle plugin unit tests, which can be run with the Gradle task
`gradle-plugin:testPython`.

However, most of the Gradle plugin functionality is covered by the integration tests.
Prerequisites:

* The test script requires the packages listed in
  `gradle-plugin/src/test/integration/requirements.txt`. It does not currently work in a
  virtualenv, so use `pip install --user` instead, making sure that you run pip with the same
  major.minor Python version as Chaquopy currently uses by default.
* On Windows, integration tests are not run with the MSYS2 Python, but rather with the `py`
  launcher (PEP 397). This is installed by default by the official Windows releases from
  python.com.

The integration tests are run by the Gradle task `gradle-plugin:testIntegration-X.Y`, where
`X.Y` is the Android Gradle plugin version to test against (e.g. `7.0`).

Each Android Gradle plugin version has a corresponding JDK version specified in
test/integration/data/base-X.Y/gradle.properties. The location of this JDK must be
set in `product/local.properties` as described above.

The full set of tests will take a long time. To run only some of them, add `-P
testPythonArgs=<args>` to the Gradle command line, where `<args>` is a space-separated list of
test classes or methods (e.g. `test_gradle_plugin.Basic.test_variant`). Other [unittest command
line options](https://docs.python.org/3/library/unittest.html#command-line-interface) can also
be given here.


# Update checklists

For component-specific checklists, see README.md files in subdirectories.

## Increasing minimum API level (minSdkVersion)

* Update `MIN_SDK_VERSION` in Common.java.
* Update `api_level` in target/build-common.sh.
* Update default API level in server/pypi/build-wheel.py.
* Search `product` directory to see if there are any workarounds which can now be removed:
  * `git ls-files | xargs -d '\n' grep -EnHi 'api.level|android.(ver|[0-9])|min.sdk|sdk.int'`
* Integration tests:
  * Update `minSdkVersion` in all test data.
  * Update expected message in `ApiLevel` tests.
  * Run all tests.
* Update documentation including versions table.
* Update demo and pkgtest apps, and test all features.
* Leave the public apps alone for now: they will be dealt with during the next release
  (see release/README.md).


## Increasing target API level (targetSdkVersion)

This should be done for each new version of Android, as soon as Google starts encouraging
developers to test against it.

* Go to the new Android version's page
  [here](https://developer.android.com/about/versions), and review the "Behavior changes"
  section to see if anything could affect the demo app or Chaquopy itself.
* Update demo and pkgtest apps, and test all features on an emulator with the new Android
  version.
* Leave the public apps alone for now: they will be dealt with during the next release
  (see release/README.md).
