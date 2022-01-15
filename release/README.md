# Product release procedure

## Runtime

Run `gradlew runtime:check`.

Run `gradlew publish`.

Record pkgtest app sizes and startup times (#5683), and investigate if significantly worse than
the previous version.

Run `gradlew -P cmakeBuildType=Release publish`.

Run Java and Python unit tests:

* Clean install, then run tests twice in the same process.
* Kill the process, then run tests again in a new process.
* Clean install the previous public release, then upgrade to the current version and run tests.
* Test "releaseMinify" variant (minify is not enabled in the "release" variant, because it
  could prevent users importing classes in the Python console).
* Change back to "debug" variant, and test a single-ABI build (temporarily change abiFilters).

Record test times in #5683, and investigate if significantly worse than the previous version.
Obviously the tests themselves may have changed, so some judgement may be required.


## Gradle plugin

On one test machine, run `gradlew -P cmakeBuildType=Release publish`. Then copy `gradle`,
`runtime` and (if necessary) `target` to the other machines. On those other machines, to make
sure the artifacts are not overwritten, temporarily disable the `dependsOn publish` line in
`gradle-plugin/build.gradle`.

On each test machine, pull the current version of this repository, then run `gradlew --continue
-P cmakeBuildType=Release gradle-plugin:check`.


## Package tests

Remove the license key from the pkgtest app, and temporarily change its build.gradle file as
follows:

* Replace the empty list in the `addPackages` line with `PACKAGE_GROUPS[1]`.
* Set `abiFilters` to x86 and x86_64 (this tests the multi-ABI case).

Then test it on the following devices, with at least one device being a clean install:

* x86 emulator with API 18 (#5316)
* x86\_64 emulator with API 21
  * TensorFlow will fail because of #5626, so test that on API 23.
* x86\_64 emulator with targetSdkVersion

On at least one device, test that the license notification and enforcement works correctly.

Restore the license key, then repeat with `PACKAGE_GROUPS[2]`.

Repeat the `PACKAGE_GROUPS[1]` and `[2]` tests on each of the following ABIs, in each case
setting `abiFilters` to just a single ABI:

* armeabi-v7a
* arm64-v8a


## Demo apps

Copy current versions of `gradle`, `runtime` and (if necessary) `target` to the public Maven
repository.

Make sure all public repositories are clean (`git clean -xdf`).

Run `release_public.sh OLD_VER NEW_VER`, where `OLD_VER` is the label in *this* repository from
which the public repositories were last updated.

If the script reports any files which require manual merging (e.g. build.gradle), examine them
and update all the public repositories as necessary.
* The public apps should use the newest Android Gradle plugin version which is at least one
  year old, and the corresponding version of Gradle. Not newer, because old versions of AGP are
  compatible with new versions of Android Studio, but not vice versa
  (https://android-developers.googleblog.com/2020/12/announcing-android-gradle-plugin.html).
  And not older, otherwise it'll be impossible to use the webserver logs to determine when it's
  safe to remove support for it.
* If .gitignore has changed, git rm any newly-ignored files.

For each of the public apps, open it in Android Studio and test it on any device.

In public `demo` project:
* Make sure license key is present.
* Generate signed APK" with "release" variant.

Use `adb` to install and test the APK on the following devices, with at least one device being
a clean install, and at least one being an upgrade from the previous public release.

* x86 emulator with minSdkVersion
* x86\_64 emulator with API 21
* x86\_64 emulator with targetSdkVersion
* Any armeabi-v7a device
* Any arm64-v8a device

Update `demo/CHANGELOG.md`.

Release app on Google Play, updating description and screenshots if necessary.

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

Commit and push all public repositories.

Commit this repository, add version number tag, and push.

Increment python/VERSION.txt for next version number.


## User communication

Post blog entry to website.

Post links to Facebook and Twitter.

Update any affected GitHub issues, StackOverflow questions, or users who contacted me directly.

If there are any packages whose announcement was postponed until this release, go through the
package release procedure in pypi/README.md.
