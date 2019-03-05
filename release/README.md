# Product release procedure

## Runtime

Run `gradlew runtime:check`.


## Gradle plugin

Free up RAM if necessary. If restarting Android Studio, do it before starting the tests, as
this may kill the Gradle daemon.

Free up disk space if necessary: the integration tests require about 6 GB per version.

On one supported workstation OS, run `gradlew -P cmakeBuildType=Release gradle-plugin:check`.

On the other supported workstation OSes, copy the `gradle` and `runtime` artifacts from the
first machine. To make sure they're not overwritten, temporarily disable the `dependsOn
publish` line in `gradle-plugin/build.gradle`. Then run the same `gradle-plugin:check` command.


## Package tests

Remove any license key from pkgtest app, then test it on the following devices, with at least
one device being a clean install:

* API 18 emulator (earlier versions give "too many libraries" error (#5316)).
* targetSdkVersion emulator
* Any armeabi-v7a device
* Any arm64-v8a device

Also, on at least one device, test that the license notification and enforcement works
correctly.


## Demo app

Copy `gradle` and `runtime` artifacts to the public Maven repository.

Make sure all public repositories are clean.

Run `release_public.sh OLD_VER NEW_VER`, where `OLD_VER` is the label in *this* repository from
which the public repositories were last updated. If the script reports any files which require
manual merging (e.g. build.gradle), examine them and update the public repositories as
necessary.

Open `public/demo` project. "Clean Project", then "Generate Signed APK". To save time, start
uploading it to Google Play now.

Test all features on the following devices, with at least one device being a clean install:

* x86 emulator with minSdkVersion
* x86 emulator with targetSdkVersion
* x86\_64 emulator with API 23 (#5563)
* Any armeabi-v7a device
* Any arm64-v8a device

Update `public/demo/CHANGELOG.md`.

Release app on Google Play, updating description and screenshots if necessary.

Copy APK to Maven repository.


## Documentation

Update `changelog.rst` and `versions.rst`.

Build and upload to server.

If major.minor version number has changed:
* Update "current" symlink.
* Add link on WordPress documentation page.


## Version control

Commit public/demo, public/console and public/hello repositories, and push to chaquo.com and
GitHub.

Commit this repository, add version number tag, and push.

Increment python/VERSION.txt for next version number.


## User communication

Post blog entry to website and Facebook.

Update any GitHub issues.

Email any affected users, including anyone who commented or gave a thumbs up to a related
issue.

If there are any packages whose announcement was postponed until this release, go through the
package release procedure below.


# Package release procedure

If this package was blocking others, use the piptest script to retry those packages and check
whether any new issues have been exposed.

If the package depended on `extractPackages` or other changes in the development version,
consider postponing the remaining steps until that version is released.

Update any GitHub issues.

Email any affected users, including anyone who emailed, commented or thumbed up a related
issue. Do the same for Kivy's issue tracker, and subscribe to their issues to discover
potential users in the future.
