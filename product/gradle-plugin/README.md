# Chaquopy Gradle plugin


## Build

For build instructions, see the README in the parent directory.


## Test

There are a few unit tests, which can be run with the Gradle task `gradle:testPython`.

However, most of the Gradle plugin functionality is covered by the integration tests.
Prerequisites:

* The test script requires the packages listed in
  `gradle-plugin/src/test/integration/requirements.txt`. It does not currently work in a
  virtualenv, so use `pip install --user` instead, making sure that you run pip with the
  same major.minor Python version as Chaquopy currently uses by default.
* On Windows, integration tests are not run with the MSYS2 Python, but rather with the
  `py` launcher (PEP 397). This is installed by default by the official Windows releases
  from python.com.

The integration tests are run by the Gradle task `gradle:testIntegration-X.Y`, where
`X.Y` is the Android Gradle plugin version to test against (e.g. `7.0`).

Each Android Gradle plugin version has a corresponding JDK version specified in
test/integration/data/base/X.Y/gradle.properties. The location of this JDK must be
set in `product/local.properties` as described above.

The full set of tests will take a long time. To run only some of them, add `-P
testPythonArgs=<args>` to the Gradle command line, where `<args>` is a space-separated
list of test classes or methods (e.g. `test_gradle_plugin.Basic.test_variant`). Other
[unittest command line
options](https://docs.python.org/3/library/unittest.html#command-line-interface) can
also be given here.


## Adding support for an Android Gradle plugin version

After first release candidate:

* Check the bundled JDK version, and update product/local.properties to point at it.
* Use the new project wizard to create an "Empty Activity" project, with "Minimum SDK"
  set to Chaquopy's current minimum.
* Create a directory integration/data/base/X.Y, where X.Y is the Android Gradle plugin
  version.
* Copy the contents from the previous base/X.Y directory, then update them with the
  settings from the "Empty Activity" project.
* Run tests on all platforms.

After stable release:

* As above, update the integration/data/base/X.Y directory with the settings from the
  new project wizard.
* Open the "product" project in the new Android Studio version, then:
  * Consider updating the Gradle version, but first see the note in
    product/gradle/wrapper/gradle-wrapper.properties.
  * Sync the project, then run the `publish` task.
  * Close the project to make sure .idea files are written.
* Update the demo and pkgtest apps as follows. Leave the public apps alone for now: they
  will be dealt with during the next release (see release/README.md).
  * In Android Studio, run Tools > AGP Upgrade Assistant.
  * Update all items from the "base" directory above.
  * Update .gitignore from the new project wizard, and git rm any newly-ignored files.
  * Test the app.
  * Close the project to make sure .idea files are written.
* Temporarily edit `test_gradle_plugin.RunGradle.rerun` to test the current stable
  Chaquopy version with the new AGP version, on all platforms.
  * If it passes, update android.rst, versions.rst and changelog.rst for the existing
    version, and publish them to the website.
  * If it fails, fix the problems, update android.rst and versions.rst for the new
    version, and perform a Chaquopy release as soon as possible, because Android
    Studio's auto-updater will cause many users to move to the new AGP version.


## Removing support for an Android Gradle plugin version

* Increment Chaquopy major version if not already done.
* Update MIN_AGP_VERSION in Common.java.
* Check if there's any version-dependent code in the plugin or the tests which can now
  be removed.
* Integration tests:
  * Remove AndroidPlugin/old, then move the old base/X.Y directory to replace it.
  * Update test_old expected message, then run the test.
* Update android.rst and versions.rst.
* Consider increasing the Gradle version of the "product" project (see
  product/gradle/wrapper/gradle-wrapper.properties).
* (Optional) Uninstall the corresponding Android Studio version to free up space, but
  first make sure it's not referenced from product/local.properties.
  * Also remove the [configuration
    directory](https://developer.android.com/studio/intro/studio-config#file_location).


## Adding support for a buildPython version

* Update `MAX_BUILD_PYTHON_VERSION` in test_gradle_plugin.py, and run the tests which
  use it.
* Run `gradle:testPython`.
* Update the list of Python versions in .github/actions/setup-python/action.yml.
* Temporarily change the `buildPython` of the demo app, comment out `pyc.pip`, and check
  it builds without any warnings other than the expected ones about .pyc compilation.
  There's no point in running it now, as the failed compilation will break many of the
  tests. We'll do this when we add runtime support for the same version (see
  target/README.md).


## Removing support for a buildPython version

* Increment Chaquopy major version if not already done.
* Update gradle-plugin/src/main/python/chaquopy/util.py.
* In test_gradle_plugin, update `OLD_BUILD_PYTHON_VERSION` and
  `MIN_BUILD_PYTHON_VERSION`, and run the tests which use them.
* Run `gradle:testPython`.
* Update the list of Python versions in .github/actions/setup-python/action.yml.
* See the comment in ci.yml about integration test runner versions, and consider
  updating them.
* Update android.rst.


## Increasing minimum API level (minSdk)

* Increment Chaquopy major version if not already done.
* Update `MIN_SDK_VERSION` in Common.java.
* Update `api_level` in target/android-env.sh.
* In server/pypi/build-wheel.py:
  * Update default API level.
  * Update `STANDARD_LIBS` with any libraries added in the new level.
* Search repository for other things that should be updated, including workarounds which
  are now unnecessary:
  * Useful regex: `api.?level|android.?ver|android \d|min.?sdk|SDK_INT`
  * Leave the public apps alone for now: they will be dealt with during the next release
    (see release/README.md).
* Integration tests:
  * Update all test data.
  * Update expected message in `ApiLevel` tests.
  * Run all tests.
* Update demo and pkgtest apps, and test all features.
* Update documentation including versions.rst.


## Increasing target API level (targetSdk)

This should be done for each new version of Android, as soon as Google starts
encouraging developers to test against it.

* Go to the new Android version's page
  [here](https://developer.android.com/about/versions), and review the "Behavior
  changes" section to see if anything could affect the demo app or Chaquopy itself.
* Update demo and pkgtest apps, and test all features on an emulator with the new
  Android version.
* Leave the public apps alone for now: they will be dealt with during the next release
  (see release/README.md).


## Updating certifi cacert.pem

* Copy cacert.pem from the newest certifi wheel on PyPI into
  gradle-plugin/src/main/resources/com/chaquo/python.
* Build the Gradle plugin.
* Use that plugin to build the demo app, and run the Python unit tests on any device
  (TestAndroidStdlib.test_ssl).
* Update the certifi version number in android.rst.


## Browsing Android Gradle plugin source code

Create a Gradle Java project in IntelliJ (NOT an Android app project) and add the Android
Gradle plugin to its compile classpath. Once the IDE has synced, you'll be able to find classes
with double-shift and use all the standard IDE navigation functions.

Alternatively, to get the original source repositories, either use the Google "repo" tool, or
do the following:

* Check out the following Android repositories at the desired version:
   * manifest
   * tools/buildSrc
   * tools/base
   * tools/gradle
   * Any other repositories referenced from tools/base/.idea/modules.xml.
* Copy files from tools/buildSrc as indicated in the manifest.
* Open tools/base as a project in IDEA.


## Updating pip, setuptools or wheel

Check out the upstream-pip branch.

Delete the package from src/main/python, including the .dist-info directory. Note that
setuptools includes some files outside of its main directory.

Download the wheel of the new version, and unpack it into src/main/python.

Commit to upstream-pip, then merge to master.

Run all integration tests.

When finished, don't forget to push the upstream-pip branch.
