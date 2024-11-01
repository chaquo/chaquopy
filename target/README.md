# Chaquopy target

This directory contains scripts to build Python for Android. They can be run on Linux or
macOS.


## Building and testing

Update Common.java with the version you want to build, and the build number you want to
give it.

Make sure the build machine has `pythonX.Y` on the PATH, where `X.Y` is the Python
major.minor version you want to build (e.g. `3.13`).

Run `python/build-and-package.sh X.Y`. This will create a release in the `maven`
directory in the root of this repository. If the packaging phase fails, e.g. because the
version already exists, then rather than doing the whole build again, you can re-run
package-target.sh directly.

If this is a new major.minor version, do the "Adding a Python version" checklist below.

Run the integration tests, starting with PythonVersion.

Temporarily change the Python version of the demo app, and run the Python and Java unit
tests on the full set of pre-release devices (see release/README.md).

To publish the build, follow the "Public release" instructions in release/README.md.
Once a version has been published on Maven Central, it cannot be changed, so any fixes
must be released under a different build number.


## Adding a Python version

* Add buildPython support for the same version (see gradle-plugin/README.md).
* In test_gradle_plugin.py, update the `PYTHON_VERSIONS` assertion.
* Update the `MAGIC` lists in test_gradle_plugin.py and pyc.py.
* Add a directory under integration/data/PythonVersion.
* Update android.rst and versions.rst.
* Build any packages used by the demo app.

When building wheels for other packages:

* Try to build all the packages we currently have in the repository for the previous
  Python version.
* For each package, in dependency order:
  * Check for notes in the meta.yaml file, in issues or in PRs.
  * Update to the current stable version, unless this would take a lot of work which
    isn't justified by user demand.
  * Review patches and build scripts to see if there are any workarounds which are no
    longer necessary.
  * In the commit message, close any issues which are now resolved.
* When finished:
  * Clear out any bad builds before copying them to the public repository.
  * Notify any users who requested new versions.


## Removing a Python version

Update all the things listed in the "Adding a Python version" section.

Search source code for `(python|version_info) *[<>=]* *[0-9]` to see if any workarounds
can now be removed.

Check if any modules can be removed from `BOOTSTRAP_NATIVE_STDLIB` in PythonTasks.kt.


## Changing the default Python version

Update `DEFAULT_PYTHON_VERSION` in Common.java.

Update the Python version in all apps in the repository.

Update the pythonX.Y scripts in integration/data/BuildPython.

See the note about the default Python micro version in
.github/actions/setup-python/action.yml.

(REST OF LIST TBD)
