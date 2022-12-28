# Chaquopy Gradle plugin

## Adding support for an Android Gradle plugin version

After first release candidate:

* Install Android Studio RC using the EXE installer.
* Use the new project wizard to create a test project.
* Integration tests:
  * Update PATH and product/local.properties to point at the bundled JDK, and restart all programs which may depend on this.
  * Add "base" directory, with the following all based on the new project wizard:
      * gradle-wrapper.properties
      * gradle.properties
      * settings.gradle
      * build.gradle
  * Run tests on all platforms.

After stable release:

* Update to stable, using the built-in updater if possible.
* Create a new test project with the new project wizard, and update the "base" directory as above.
* Update the following apps with settings from the new project wizard: demo, pkgtest, piptest. Leave the public apps alone for now: they will be dealt with during the next release (see release/README.md).
  * Update all items listed under "base" directory above.
  * Update .gitignore file, and git rm any newly-ignored files.
  * Test the app.
* Sync the "product" project in the new Android Studio version in case of any .idea file updates, but see note in product/gradle/wrapper/gradle-wrapper.properties before updating the Gradle version.
* Run integration tests on all platforms.
* If we're not already planning to make a Chaquopy release soon, temporarily edit
  `test_gradle_plugin.RunGradle.rerun` to test the released Chaquopy version with the new
  AGP version.
  * If it passes, update android.rst and versions.rst for the existing version, add a note
    in changelog.rst, and publish them to the website.
  * If it fails, perform a Chaquopy release as soon as possible, because Android Studio's
    auto-updater will cause many users to move to the new AGP version.


## Removing support for an Android Gradle plugin version

* Increment Chaquopy major version if not already done.
* Update MIN_ANDROID_PLUGIN_VER in PythonPlugin.
* Integration tests:
  * Remove AndroidPlugin/old, then move the old base-X.Y directory to replace it.
  * Update test_old expected message, then run the test.
* Update android.rst and versions.rst.
* Consider increasing the Gradle version of the "product" project (see product/gradle/wrapper/gradle-wrapper.properties).
* (Optional) Uninstall the corresponding Android Studio version to free up space:
  * Check note about `javaHome` in product/runtime/build.gradle.
  * If bundled JDK was in the PATH or product/local.properties, update them, and restart all programs which may depend on this.
  * Run uninstaller in program directory.
  * Remove configuration directory (AppData/Roaming/Google/AndroidStudioX.Y)


## Adding support for a buildPython version

* Update `MAX_BUILD_PYTHON_VERSION` in test_gradle_plugin.py, and run the tests which use
  it.


## Removing support for a buildPython version

* Update gradle-plugin/src/main/python/chaquopy/util.py.
* Update `testPython` in gradle-plugin/build.gradle, and run the tests.
* Update `OLD_BUILD_PYTHON_VERSION` and `MIN_BUILD_PYTHON_VERSION` in test_gradle_plugin,
  and run the tests which use them.
* Update android.rst.


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

Delete the relevant directories in src/main/python, including the .dist-info directory. Note
that pkg_resources is part of setuptools.

Download the wheel of the new version, and unpack it into src/main/python.

Commit to upstream-pip, then merge to master.

Run all integration tests.

When finished, don't forget to push the upstream-pip branch.
