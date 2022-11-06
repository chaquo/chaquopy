# Product release procedure

## Runtime

Run `gradlew runtime:check`.

Run `gradlew -P cmakeBuildType=Release publish`.

Record pkgtest app sizes and startup times (#5683), and investigate if significantly worse than
the previous version. Remember that the tests and the packages themselves may have changed.

Open demo app, and run the Java and Python unit tests on any device under the following
conditions:

* Set build variant to "debug".
* Clean install, then run tests twice in the same process.
* Kill the process, then run tests again in a new process.
* Test "releaseMinify" variant (minify is not enabled in the "release" variant, because it
  could prevent users importing classes in the Python console).
* Change back to "debug" variant, and test a single-ABI build by temporarily changing
  abiFilters.

Run Build > Generate Signed APK with the "release" variant. Save a copy of this APK,
because we'll be releasing it on Google Play later.

Use `adb` to install and test the APK on the following devices, with at least one device being
a clean install, and at least one being an upgrade from the previous public release with the
tests already run.

* x86 emulator with minSdkVersion
* x86_64 emulator with minSdkVersion
* x86_64 emulator with targetSdkVersion
* Any armeabi-v7a device
* Any arm64-v8a device

Record test times in #5683, and investigate if significantly worse than the previous version.
Remember that the tests themselves may have changed.

Test all the UI elements of the app on both minSdkVersion and targetSdkVersion.

Test all the non-default Python versions on the same devices.


## Gradle plugin

On one test machine, run `gradlew -P cmakeBuildType=Release publish`. Then copy `gradle`,
`runtime` and (if necessary) `target` to the other machines. On those other machines, to make
sure the artifacts are not overwritten, temporarily disable the `dependsOn publish` line in
`gradle-plugin/build.gradle`.

On each test machine, pull the current version of this repository, then run `gradlew --continue
-P cmakeBuildType=Release gradle:check`.


## Package tests

The following builds and tests can take a long time, and it's helpful to parallelize them
as much as possible. So after each build, copy the APK out of the build directory and
install it while running the next build. This is why we test the slowest devices first.

Temporarily edit pkgtest/app/build.gradle to replace the empty list in the `addPackages`
line with `PACKAGE_GROUPS[1]`.

Set `abiFilters` to each of the following values, and test on a corresponding device:

* armeabi-v7a (use a 32-bit device)
* arm64-v8a

Set `abiFilters` to `"x86", "x86_64"` (this tests the multi-ABI case), and test on the
following devices, with at least one being a clean install:

* x86 emulator with minSdkVersion
* x86_64 emulator with minSdkVersion
  * TensorFlow will fail because of #5626, so test that on API 23.
* x86_64 emulator with targetSdkVersion

Repeat with `PACKAGE_GROUPS[2]`.


## Public release

Use release/bundle.sh to create bundle JARs for the following things, and [release them to
Maven Central](https://central.sonatype.org/publish/publish-manual/#bundle-creation):

* `com.chaquo.python.gradle.plugin`
* `gradle`
* `runtime/*`
* `target` (if updated)

As a backup, also upload them to <https://chaquo.com/maven-central>.


## Demo apps

Make sure all public repositories are clean (`git clean -xdf`).

Run `release/release_public.sh OLD_VER NEW_VER`, where `OLD_VER` is the label in *this*
repository from which the public repositories were last updated.

If the script reports any files which require manual merging (e.g. build.gradle), examine them
and update all the public repositories as necessary.
* The public apps should use the newest Android Gradle plugin version which is at least one
  year old. Not newer, because new versions of AGP are incompatible with old versions of
  Android Studio
  (https://android-developers.googleblog.com/2020/12/announcing-android-gradle-plugin.html).
  And not older, otherwise it'll be impossible to use the webserver logs to determine when it's
  safe to remove support for it.
* If updating the AGP version, also update to the corresponding versions of these things
  (see the integration tests):
  * Gradle
  * gradle.properties
  * Kotlin plugin
* If .gitignore has changed, git rm any newly-ignored files.

Open each public app in Android Studio and test it on any device, with a clean install.

Take the signed APK of the demo app which was built above, and release it on Google Play,
updating description and screenshots if necessary.

Set reminder to check for Google Play crash reports regularly over the next month.


## Documentation

Update:
* `changelog.rst`
* `versions.rst`
* `release` in `conf.py`

Run `gradlew runtime:doc`, and upload to server.

If major.minor version number has changed:
* Update "current" symlink.
* Add link on WordPress documentation page.


## Version control

Commit and push all example app repositories.

Commit this repository, add version number tag, and push.

Increment python/VERSION.txt for next version number.


## User communication

Post blog entry to website.

Post links to Facebook and Twitter.

Update any affected GitHub issues, StackOverflow questions, or users who contacted me directly.

If there are any packages whose announcement was postponed until this release, go through the
package release procedure in pypi/README.md.
