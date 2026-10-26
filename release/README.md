# Product release procedure

## Integration tests

These are fully automated in GitHub Actions. Check the most recent run succeeded, and
make a note of its commit, because we'll be tagging it later.

On all machines that will be used during the release:

* Update to the head of the master branch, and make sure the repository is clean.
* Download the `maven` artifact from GitHub Actions, and unpack it into the local
  `maven` directory.


## BeeWare compatibility tests

Pull the current versions of briefcase, toga and briefcase-android-gradle-template, and
make sure the repositories are clean.

In a virtual environment, install the Briefcase repository in editable mode.

Edit briefcase-android-gradle-template to use the new Chaquopy version, and temporarily
add a `repositories` entry pointing at the artifacts you downloaded above, e.g.:

    maven { url "/Users/msmith/git/chaquo/chaquopy/maven" }

Use that template to run the Toga testbed on the default Briefcase emulator, e.g.:

   briefcase create android -a testbed -C 'template="/Users/msmith/git/beeware/briefcase-android-gradle-template"'
   briefcase run android -a testbed --test -ur

It might be difficult to get a 100% pass on a local emulator, but at least make sure
it's no worse than the previous version of the template.

We will create a template PR in a later step below.


## Unit tests

Open the demo app in Android Studio, and run the Java and Python unit tests on any
device under the following conditions:

* Set build variant to "debug".
* Clean install, then run tests twice in the same process.
* Kill the process, then run tests again in a new process.
* Test "release" variant".
* Test "releaseMinify" variant (minify is not enabled in the "release" variant, because it
  could prevent users importing classes in the Python console).
* Change back to "debug" variant, and test a single-ABI build by temporarily changing
  abiFilters.

Using either Android Studio or the CPython testbed launcher, run the Python unit tests
on all ABIs, with at least one test covering each of the following:

* A physical device
* minSdk (or as close as possible, on all ABIs)
* targetSdk
* 16 KB pages (on all 64-bit ABIs)
* A clean install

Repeat for each of the non-default Python versions.

Download the `demo` artifact from GitHub Actions, and test its APK on both minSdk and
targetSdk, including:

* An upgrade from the previous Google Play release, with the tests already run.
* All the UI elements of the app.
* The Java and Python unit tests.


## Performance tests

Open the pkgtest app in Android Studio, and temporarily edit the top-level build.gradle
file to use the local Chaquopy version.

Record performance data in performance.md, and investigate if significantly worse than
the previous version. Remember that the tests, the packages, and their dependencies may
all have changed.


## Package tests

On all machines that will be used for these tests, temporarily edit the pkgtest app:

* In the top-level build.gradle file, use the local Chaquopy version.

* In the app/build.gradle file, set `PACKAGES` to the top 40 binary packages for the
  default Python version, ordered by number of PyPI downloads. As of 2026-10, this is:

    cryptography cffi pyyaml numpy markupsafe pandas multidict yarl pillow frozenlist greenlet grpcio lxml regex scipy psutil scikit-learn pynacl matplotlib zstandard kiwisolver bcrypt google-crc32c contourpy tornado pyzmq brotli lz4 pycryptodome ruamel-yaml-clib argon2-cffi-bindings shapely zope-interface pycryptodomex statsmodels opencv-python ujson sentencepiece gevent scikit-image

To update this list:

* Get the [PyPI statistics in CSV format](https://hugovk.github.io/top-pypi-packages/).
* `cd /var/www/chaquo/pypi-13.1`
* `cat path/to/top-pypi-packages.csv | tail -n +2 | head -n 2000 | cut -d, -f2 | tr -d '"' | while read name; do if ls $name/*cp310* &>/dev/null; then echo $name; fi; done | grep -vE '^opencv.*(contrib|headless)|^(argon2-cffi|aiohttp)$' | head -n40 | tr '\n' ' '`
  * The `opencv` variants all use the same runtime package name.
  * `argon2-cffi` and `aiohttp` have newer versions available as pure-Python wheels.
* TODO: once the default version is 3.13 or later, also include data from
  https://beeware.org/mobile-wheels.

Search the package test scripts for the word "Android", and consider adding any packages
which test Chaquopy (as opposed to the package itself) in a way that isn't covered by
Chaquopy's own unit tests.

Test on the full set of pre-release devices above, with the following modifications:

* 16 KB pages aren't necessary until the default Python version is 3.13 or later.
* There should be at least one test each for a single-ABI build, and a multi-ABI build.


## Maven Central release

Use release/bundle.sh to create a bundle with the following things, and [release it to
Maven Central](https://central.sonatype.org/publish/publish-portal-upload/):

* `com.chaquo.python.gradle.plugin`
* `gradle`
* `runtime/*`
* `target` (if necessary)

As a backup, also upload them to <https://chaquo.com/maven-central>.


## Example apps

Make sure all the target repositories are clean (`git clean -xdf`).

Run `release/release_public.sh OLD_VER NEW_VER`, where `OLD_VER` is the label in *this*
repository from which the target repositories were last updated.

If the script reports any files which require manual merging (e.g. build.gradle),
examine them and update all the target repositories as necessary.
* The example apps should use an Android Gradle plugin version which is at least one year
  old, because new versions of AGP are incompatible with old versions of Android Studio
  (https://android-developers.googleblog.com/2020/12/announcing-android-gradle-plugin.html).
* If updating the AGP version, also update to the corresponding versions of these things
  (see the integration tests):
  * Gradle
  * gradle.properties
* If .gitignore has changed, git rm any newly-ignored files.

Wait for the Maven Central release to be available.

Open each app in Android Studio and test it on minSdk and targetSdk, with a clean
install.

Close the projects to make sure .idea files are written.

Commit and push all example app repositories.

Take the demo app APK which was tested above, and release it on Google Play, updating
the description and screenshots if necessary.

Set a reminder to check for Google Play crash reports regularly over the next month.


## Documentation

Add news fragments as necessary, and check the release notes by running `towncrier build
--version VERSION --draft`. Once happy, save the fragments in a separate commit, because
they'll be deleted when running `towncrier` in non-draft mode.

Update:
* `changelog.rst`, by running the above `towncrier` command without `--draft`.
* `versions.rst`
* `release` in `conf.py`

In the `product` directory, run `gradlew runtime:docs`, and check the output.

Upload documentation to the webserver. If the major.minor version number has changed:
* Update the "current" symlink (`ln -sfn`).
* Add a link on the WordPress documentation page.


## Version control

Tag the commit the GitHub Actions artifacts were built from, and push the tag.

Create a release page on GitHub with a link to the change log section.

Close the GitHub milestone.

Increment the micro version number in VERSION.txt. Then in the `product` directory, run
`gradlew publish`.

Commit and push this repository.

Remove the temporary `maven` repository from briefcase-android-gradle-template, and
create a PR.


## Announcements

Post blog entry to website.

Post link to X, and enable "only accounts you mention can reply", because it doesn't
reliably send email notifications of replies. Enabling replies and apparently ignoring
them would make us look worse than not enabling replies at all.
