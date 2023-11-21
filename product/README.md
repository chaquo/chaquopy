# Chaquopy product

This directory contains a Gradle project with the following sub-projects:

* `gradle-plugin` contains the Chaquopy Gradle plugin.
* `runtime` contains the Chaquopy runtime libraries.


## Build

First, install the following things:

* A local Python installation for each Python major.minor version suported by Chaquopy
  (list them with `target/list-versions.py --minor`). These must be on the PATH as
  `pythonX.Y` on Unix, or `py -X.Y` on Windows.
  * On Linux, install them from your distribution, or use Miniconda.
  * On Mac and Windows, download them from https://python.org/.

* Android Python headers and libraries in target/prefix. These can be installed using
  the download-target.sh and unpackage-target.sh scripts, as shown in ci.yml.

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

The build can be done either at the command line using `gradlew`, or by opening the
project in Android Studio. The main Gradle tasks are `gradle:publish` and
`runtime:publish`. For a release build, add `-P cmakeBuildType=Release` to the Gradle
command line.

All artifacts are generated in the `maven` directory in the root of this Git repository, and
all apps in the repository are set to give that directory higher priority than the public Maven
server.


## Test

For test instructions, see the README files in each subdirectory.


## Documentation

Documentation is built by the following Gradle tasks:

* `runtime:sphinx` for the main pages (source files are in runtime/docs/sphinx)
* `runtime:javadoc` for the Java API documentation

`runtime:docs` will build them all.
