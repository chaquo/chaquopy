# Product release procedure

## Runtime

Run `gradlew runtime:check`.

Temporarily set the demo app to a single ABI, and run unit tests on any device.

Restore it to the full set of ABIs, then run unit tests on any device.

Make sure unit tests work when run twice in succession.

Check app sizes and startup times compared to previous version (#5620).


## Gradle plugin

Free up RAM if necessary. If restarting Android Studio, do it before starting the tests, as
this may kill the Gradle daemon.

Free up disk space if necessary: the integration tests require about 6 GB per Android Gradle
plugin version.

On one supported workstation OS, run `gradlew --continue -P cmakeBuildType=Release
gradle-plugin:check`.

On the other supported workstation OSes, copy the `gradle` and `runtime` artifacts from the
first machine. To make sure they're not overwritten, temporarily disable the `dependsOn
publish` line in `gradle-plugin/build.gradle`. Then run the same `gradle-plugin:check` command.


## Package tests

Remove license key from pkgtest app, and temporarily set it to include all packages by passing
`null` to `addPackages`.

Temporarily set `abiFilters` to x86 and x86_64 (this tests the multi-ABI case), then test it on
the following devices, with at least one device being a clean install:

* x86 emulator with API 18 (#5316)
* x86 emulator with targetSdkVersion
* x86\_64 emulator with API 21
  * TensorFlow will fail because of #5626, so test that on API 23.

Then test the following, in each case setting `abiFilters` to just a single ABI, and with at
least one device being a clean install:

* Any armeabi-v7a device
* Any arm64-v8a device

On at least one device, test that the license notification and enforcement works correctly.

Do an all-ABI test of opencv-contrib-python and pycrypto, and possibly some of the other
entries in `DEFAULT_EXCLUDE_PACKAGES`.


## Demo apps

Copy current versions of `gradle`, `runtime` and (if necessary) `target` to the public Maven
repository.

Make sure all public repositories are clean.

Run `release_public.sh OLD_VER NEW_VER`, where `OLD_VER` is the label in *this* repository from
which the public repositories were last updated. If the script reports any files which require
manual merging (e.g. build.gradle), examine them and update the public repositories as
necessary.

For each of the following simple demo apps, "Clean Project", then test it on any device:

* `console`
* `hello`

Open public `demo` project. "Clean Project", then "Generate Signed APK" with "release" variant
and all signature schemes.

Use `adb` to install and test the APK on the following devices, with at least one device being
a clean install, and at least one being an upgrade from the previous public release.

* x86 emulator with minSdkVersion
* x86 emulator with targetSdkVersion
* x86\_64 emulator with API 21
* Any armeabi-v7a device
* Any arm64-v8a device

Update `demo/CHANGELOG.md`.

Release app on Google Play, updating description and screenshots if necessary.

Copy APK to the public Maven repository.

Set reminder to check for Google Play crash reports regularly over the next month.


## Documentation

Update `changelog.rst` and `versions.rst`.

Run `gradlew runtime:doc`, and upload to server.

If major.minor version number has changed:
* Update "current" symlink.
* Add link on WordPress documentation page.


## Version control

Commit public/demo, public/console and public/hello repositories, and push to chaquo.com and
GitHub.

Commit this repository, add version number tag, and push.

Increment python/VERSION.txt for next version number.


## User communication

Post blog entry to website.

Post links to Facebook and Twitter.

Update any GitHub issues, and notify any affected users who contacted us outside of GitHub.

If there are any packages whose announcement was postponed until this release, go through the
package release procedure in pypi/README.md.
