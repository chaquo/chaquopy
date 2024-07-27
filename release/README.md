# Product release procedure

## Integration tests

These are fully automated in GitHub Actions. Check the most recent run succeeded, and
make a note of its commit, because we'll be tagging it later.

Download the `maven` artifact from GitHub Actions, and unpack it into the local `maven`
directory on all machines that will be used by the subsequent tests.


## Unit tests

Open the demo app in Android Studio, and run the Java and Python unit tests on a
representative device under the following conditions:

* Set build variant to "debug".
* Clean install, then run tests twice in the same process.
* Kill the process, then run tests again in a new process.
* Test "release" variant".
* Test "releaseMinify" variant (minify is not enabled in the "release" variant, because it
  could prevent users importing classes in the Python console).
* Change back to "debug" variant, and test a single-ABI build by temporarily changing
  abiFilters.

Download the `demo` artifact from GitHub Actions, and unpack the APK from it.

Install the APK and run the Java and Python unit tests on the following devices, with at
least one device being a clean install, and at least one being an upgrade from the
previous public release with the tests already run.

* x86 emulator with minSdkVersion
* x86_64 emulator with minSdkVersion
* x86_64 emulator with targetSdkVersion
* Any armeabi-v7a device
* Any arm64-v8a device

Test all the UI elements of the app on both minSdkVersion and targetSdkVersion.

For each of the non-default Python versions, run the Java and Python unit tests on the
same devices.


## Performance tests

Open the pkgtest app in Android Studio, and temporarily edit the top-level build.gradle
file to use the local Chaquopy version.

Record performance data in performance.md, and investigate if significantly worse than
the previous version. Remember that the tests and the packages themselves may have
changed.


## Package tests

Open the pkgtest app in Android Studio, and temporarily edit the top-level build.gradle
file to use the local Chaquopy version.

Temporarily edit the app/build.gradle file to set `PACKAGES` to the top 40 recipes,
ordered by number of PyPI downloads:

* Get the PyPI statistics as described in server/pypi/README-internal.md.
* `cd server/pypi/packages`
* `cat pypi-downloads.csv | cut -d, -f1 | while read name; do if [ -e $name ]; then echo $name; fi; done | head -n40 | tr '\n' ' '`

As of 2023-12, this is:

    numpy cryptography cffi pandas aiohttp yarl greenlet frozenlist grpcio lxml psutil multidict pillow scipy bcrypt matplotlib pynacl scikit-learn kiwisolver regex ruamel-yaml-clib google-crc32c pycryptodomex contourpy pyzmq pycryptodome zope-interface tensorflow h5py tokenizers torch shapely numba llvmlite xgboost scikit-image statsmodels sentencepiece opencv-python torchvision

Search the package test scripts for the word "Android", and consider adding any packages
which test Chaquopy in a way that isn't covered by the unit tests.

Set `abiFilters` to each of the following values (this tests the single-ABI case), and
test on a corresponding device:

* armeabi-v7a (use a 32-bit device)
* arm64-v8a

Set `abiFilters` to `"x86", "x86_64"` (this tests the multi-ABI case), and test on the
following devices, with at least one being a clean install:

* x86 emulator with minSdkVersion
* x86_64 emulator with minSdkVersion (TensorFlow is expected to fail because of #669)
* x86_64 emulator with targetSdkVersion


## Public release

Use release/bundle.sh to create bundle JARs for the following things, and [release them to
Maven Central](https://central.sonatype.org/publish/publish-manual/#bundle-creation):

* `com.chaquo.python.gradle.plugin`
* `gradle`
* `runtime/*`
* `target` (if necessary)

As a backup, also upload them to <https://chaquo.com/maven-central>.


## Demo apps

Make sure all public repositories are clean (`git clean -xdf`).

Run `release/release_public.sh OLD_VER NEW_VER`, where `OLD_VER` is the label in *this*
repository from which the public repositories were last updated.

If the script reports any files which require manual merging (e.g. build.gradle), examine them
and update all the public repositories as necessary.
* The public apps should use an Android Gradle plugin version which is at least one year
  old, because new versions of AGP are incompatible with old versions of Android Studio
  (https://android-developers.googleblog.com/2020/12/announcing-android-gradle-plugin.html).
* If updating the AGP version, also update to the corresponding versions of these things
  (see the integration tests):
  * Gradle
  * gradle.properties
  * Kotlin plugin
* If .gitignore has changed, git rm any newly-ignored files.

Open each public app in Android Studio and test it on any device, with a clean install.

Close the projects to make sure .idea files are written.

Take the demo app APK which was tested above, and release it on Google Play, updating
the description and screenshots if necessary.

Set reminder to check for Google Play crash reports regularly over the next month.


## Documentation

Add news fragments as necessary, and check the release notes by running `towncrier build
--version VERSION --draft`. Once happy, save the fragments in a separate commit, because
they'll be deleted when running `towncrier` in non-draft mode.

Update:
* `changelog.rst`, by running the above `towncrier` command without `--draft`.
* `versions.rst`
* `release` in `conf.py`

Run `gradlew runtime:doc`, and upload to server.

If major.minor version number has changed:
* Update "current" symlink.
* Add link on WordPress documentation page.


## Version control

Commit and push all example app repositories.

Tag the commit the GitHub Actions artifacts were built from, and push the tag.

Commit and push this repository.

Increment VERSION.txt for next version number.


## User communication

Create release page on GitHub with a link to the change log section.

Post blog entry to website.

Post link to X, and enable "only accounts you mention can reply", because it doesn't
reliably send email notifications of replies. Enabling replies and apparently ignoring
them would make us look worse than not enabling replies at all.

Update any affected GitHub issues, StackOverflow questions, email threads, etc.

If there are any packages whose announcement was postponed until this release, go
through the package release procedure in pypi/README-internal.md.
