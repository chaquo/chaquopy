# Product release procedure

## Integration tests

These are fully automated in GitHub Actions. Check the most recent run succeeded, and
make a note of its commit, because we'll be tagging it later.

Download the `maven` artifact from GitHub Actions, and unpack it into the local `maven`
directory on all machines that will be used by the subsequent tests.


## BeeWare compatibility tests

Pull the current versions of briefcase, toga and briefcase-android-gradle-template.

Edit briefcase-android-gradle-template to use the new Chaquopy version, and temporarily
add a `repositories` entry pointing at the artifacts you downloaded above, e.g.:

   maven { url "/Users/msmith/git/chaquo/chaquopy/maven" }

Use that template to run the Toga testbed.

We will create a Briefcase PR in the final step below.


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

Download the `demo` artifact from GitHub Actions, and unpack the APK from it.

Install the APK and run the Java and Python unit tests on all ABIs, with at least one
device being each of the following:

* A physical device (on all ABIs if possible)
* minSdk (on all ABIs if possible)
* targetSdk
* 16 KB pages
* A clean install
* An upgrade from the previous public release, with the tests already run

Test all the UI elements of the app on both minSdkVersion and targetSdkVersion.

For each of the non-default Python versions, run the Java and Python unit tests on the
same devices.


## Performance tests

Open the pkgtest app in Android Studio, and temporarily edit the top-level build.gradle
file to use the local Chaquopy version.

Record performance data in performance.md, and investigate if significantly worse than
the previous version. Remember that the tests, the packages, and their dependencies may
all have changed.


## Package tests

Open the pkgtest app in Android Studio, and temporarily edit the top-level build.gradle
file to use the local Chaquopy version.

Temporarily edit the app/build.gradle file to set `PACKAGES` to the top 40 recipes for
the default Python version, ordered by number of PyPI downloads:

* Get the [PyPI statistics in CSV format](https://hugovk.github.io/top-pypi-packages/).
* `cd /var/www/chaquo/pypi-13.1`
* `cat path/to/top-pypi-packages.csv | tail -n +2 | head -n 2000 | cut -d, -f2 | tr -d '"' | while read name; do if ls $name/*cp310* &>/dev/null; then echo $name; fi; done | grep -vE 'opencv.*(contrib|headless)|^argon2-cffi$' | head -n40 | tr '\n' ' '`
* TODO: once the default version is 3.13 or later, also include data from
  https://beeware.org/mobile-wheels.

As of 2025-11, this is:

    numpy cryptography cffi pandas aiohttp yarl multidict frozenlist greenlet pillow grpcio psutil scipy lxml regex pynacl scikit-learn bcrypt matplotlib zstandard google-crc32c kiwisolver contourpy ruamel-yaml-clib pyzmq shapely pycryptodome brotli lz4 zope-interface pycryptodomex argon2-cffi-bindings sentencepiece opencv-python gevent ujson statsmodels scikit-image spacy bitarray

Search the package test scripts for the word "Android", and consider adding any packages
which test Chaquopy (as opposed to the package itself) in a way that isn't covered by
Chaquopy's own unit tests.

Set `abiFilters` to each of `armeabi-v7a` and `arm64-v8a` (this tests the single-ABI
case), and test on those ABIs, with at least one device being each of the following:

* A physical device (on all ABIs if possible)
* minSdk (on all ABIs if possible)
* targetSdk
* TODO: once the default version is 3.13 or later, include a device with 16 KB pages.
* A clean install

Set `abiFilters` to `"x86", "x86_64"` (this tests the multi-ABI case), and test on those
ABIs, with at least one device being each of the following:

* minSdk (on all ABIs if possible)


## Public release

Use release/bundle.sh to create bundles for the following things, and [release them to
Maven Central](https://central.sonatype.org/publish/publish-portal-upload/):

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

Open each public app in Android Studio and test it on minSdk and targetSdk, with a clean
install.

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

Run `gradlew runtime:doc`, and check the output. It will be released in the final step
below.


## Version control

Commit and push all example app repositories.

Tag the commit the GitHub Actions artifacts were built from, and push the tag.

Increment the micro version number in VERSION.txt.

Commit and push this repository.


## Once the Maven Central release is live

Upload documentation to the webserver. If the major.minor version number has changed:
* Update the "current" symlink (`ln -sfT`).
* Add a link on the WordPress documentation page.

Create release page on GitHub with a link to the change log section.

Post blog entry to website.

Post link to X, and enable "only accounts you mention can reply", because it doesn't
reliably send email notifications of replies. Enabling replies and apparently ignoring
them would make us look worse than not enabling replies at all.

Remove the temporary `maven` repository from briefcase-android-gradle-template, and
create a PR.

On the Python wiki, update the Android and GuiProgramming pages, and remove obsolete
projects.
