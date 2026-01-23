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

* Check the bundled JDK version, and update product/local.properties to point at it.
* Use the new project wizard to create an "Empty Activity" project, with "Minimum SDK"
  set to Chaquopy's current minimum.
* Create a directory integration/data/base/X.Y, where X.Y is the Android Gradle plugin
  version.
* Copy the contents from the previous base/X.Y directory, then update them with the
  settings from the "Empty Activity" project.
* In test_gradle_plugin.py, temporarily change `chaquopyVersion` to the current stable
  Chaquopy version, and make sure that version isn't in the local Maven repository so it
  will be downloaded from Maven Central.
* Run all integration tests against the new AGP version.
  * If it passes, update android.rst, versions.rst and changelog.rst for the existing
    version, and publish them to the website.
  * If it fails, plan to perform a Chaquopy release as soon as possible, because Android
    Studio's auto-updater will cause many users to move to the new AGP version.
* Revert the changes to test_gradle_plugin.py, then run all integration tests against
  the Chaquopy development version and the new AGP version.

* Open the "product" project in the new Android Studio version, then:
  * Sync the project.
  * Test it by running the `publish` task.
* Update the demo and pkgtest apps as follows. Leave the public apps alone for now: they
  will be dealt with during the next release (see release/README.md).
  * In Android Studio, run Tools > AGP Upgrade Assistant. If this applies any
    compatibility settings which are no longer the default, try to use the recommended
    settings instead.
  * Apply any other updates from the "base" directory above.
  * Test the app.
* Close all projects to make sure .idea files are written.
* Add .gitignore entries if necessary.


## Removing support for an Android Gradle plugin version

* Increment Chaquopy major version if not already done.
* Update MIN_AGP_VERSION in Common.java.
* Check if there's any version-dependent code in the plugin or the tests which can now
  be removed.
* Integration tests:
  * Update test_old expected message, then run the test.
* Update android.rst and versions.rst.
* (Optional) Uninstall the corresponding Android Studio version to free up space, but
  first make sure it's not referenced from product/local.properties.
  * Also remove the [configuration
    directory](https://developer.android.com/studio/intro/studio-config#file_location).


## Adding a Python version

Target:

* Update Common.java.
* Build the target packages as described in target/README.md.

Product:

* In test_gradle_plugin.py, update the `PYTHON_VERSIONS` assertion.
* Update the `MAGIC` lists in test_gradle_plugin.py and pyc.py.
* Update .github/actions/setup-python/action.yml.
* Update android.rst and versions.rst.

Tests (this list is referenced from target/README.md):

* Run `gradle:testPython`.
* Run `Dsl` integration test, and update stdlib modules list as necessary.
* Run pkgtest app with no packages, and verify you can get as far as the Python console.
  This may require further updates to `BOOTSTRAP_NATIVE_STDLIB`.
* Build, test and release any packages used by the demo app and integration tests.
* Run all integration tests.
* Temporarily change the Python version of the demo app, and run the Python and Java
  unit tests on the full set of pre-release devices (see release/README.md).
* Release the target packages to Maven Central (see release/README.md).


## Removing a Python version

* Increment Chaquopy major version if not already done.
* Update any references in the integration tests, including the names of the pythonX.Y
  scripts in data/BuildPython.
* Search repository to see if any code can now be simplified. Useful regex:
  * `(python( version)?|version_info) *[<>=]* *\(?\d[,.] *\d`
* Check if any modules can be removed from `BOOTSTRAP_NATIVE_STDLIB` in PythonTasks.kt.
* Update and test all the things listed in the "Adding a Python version" section.


## Changing the default Python version

* Update `DEFAULT_PYTHON_VERSION` in Common.java and test_gradle_plugin.py.
* Update and test all the things listed in the "Adding / Removing a Python version"
  sections.
* Update the Python version in all apps in the repository, and test them.


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
* Update `COMPILE_SDK_VERSION` in Common.java, and rebuild the `product` project.
* In the demo and pkgtest apps:
  * Update `compileSdk` and `targetSdk`. The IDE may prompt you to use the SDK Upgrade
    Assistant, but all that does is show you the same content as the pages above,
    filtered for what it believes is relevant to the current app.
  * Test all features on an emulator with the new Android version.
* Leave the public apps alone for now: they will be dealt with during the next release
  (see release/README.md).
* Consider also updating the targetSdk in:
  * The CPython Android testbed.
  * The Briefcase Android template, including running Toga's automated tests, and doing
    a basic manual test of a Toga app.


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


## Updating pip

Check out the upstream-pip branch.

Delete pip from src/main/python, including the .dist-info directory.

Download the wheel of the new version, and unpack it into src/main/python.

Commit to upstream-pip, then merge to master.

Run all integration tests.

When finished, don't forget to push the upstream-pip branch.
