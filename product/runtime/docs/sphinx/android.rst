.. highlight:: none

Android instructions
####################

Chaquopy is distributed as a plugin for the Android Gradle build system. For a full example of
how to use it, see the `demo app <https://github.com/chaquo/chaquopy>`_.

Setup
=====

Installation
------------

Prerequisites:

* Android Gradle plugin version 2.3.x (this is usually the same as the Android Studio version)
* `minSdkVersion` 9 or higher

In the project's top-level `build.gradle` file, add the following lines to the existing
`repositories` and `dependencies` blocks:

.. parsed-literal::
    buildscript {
        repositories {
            maven { url "https://chaquo.com/maven" }
        }
        dependencies {
            classpath "com.chaquo.python:gradle:|release|"
        }
    }

In the app's module-level `build.gradle` file, apply the Chaquopy plugin at the top of the
file, but after the Android plugin::

   apply plugin: "com.chaquo.python"  // Must come after com.android.application


Python version
--------------

The Python version must be specified. Currently the only available version is 2.7.10::

    android {
        defaultConfig {
            python {
               version "2.7.10"
            }
        }
    }

ABI filters
-----------

Chaquopy does not require the Android native development kit (NDK). However, the Python
interpreter is a native component, so you must still specify which native ABIs you want the app
to support.

Currently available ABIs are `x86` (for the Android emulator) and `armeabi-v7a` (for the vast
majority of Android hardware)::

    android {
        defaultConfig {
            ndk {
               abiFilters "x86", "armeabi-v7a"
            }
        }
    }

.. note:: Each ABI will add several MB to the size of the app.


Development
===========

Python code
-----------

Place Python source code in `src/main/python`, and Chaquopy will automatically build it into
the app.

Python requirements
-------------------

External dependencies may be built into the app by giving a `pip install
<https://pip.readthedocs.io/en/stable/reference/pip_install/>`_ command line. This may specify
an exact requirement, a local wheel file, or a requirements file.

.. note:: Chaquopy currently only supports pure-Python wheel files: it will not accept sdist
          packages or architecture-specific wheels.

::

    python {
        pipInstall "six==1.10.0"
        pipInstall "mypackage-1.2.3-py2.py3-none-any.whl"
        pipInstall "-r", "requirements.txt"
    }

Any other `pip install` options may also be specified, except the following:

* Target environment options, such as `--target` and `--user`.
* Installation format options, such as `-e` and `--egg`.
* Package type options, such as `--no-binary`.

Chaquopy comes with its own copy of `pip`, but it requires Python to be available on the build
machine to run it. If `python` is not on your `PATH`, or you want to use a different version,
use the `buildPython` setting::

    python {
        buildPython "python3"  // Assuming "python3" is on your PATH
        buildPython "C:/Python27/python.exe"  // Typical Windows installation
    }

Licensing
=========

A license is required in order to distribute apps built with Chaquopy. The unlicensed version
is fully-functional, but will display a notification whenever the app is started.

All licenses include upgrades to future versions of Chaquopy.

Commercial license
------------------

A commercial license allows unlimited use of Chaquopy by a single developer. While Chaquopy is
in beta, licenses are available free of charge. Please `contact us
<https://chaquo.com/chaquopy/contact/>`_ to obtain a license key.

Once you have a key, add the following line to the project's `local.properties` file::

    chaquopy.license=<license key>

Open-source license
-------------------

If your app is open-source, you may obtain a license for it free of charge. Please `contact us
<https://chaquo.com/chaquopy/contact/>`_ with details of your app, including:

* The app ID (package name)
* Where the app is distributed (e.g. Google Play)
* Where the app's source code is available

Once the app ID is activated on our server, anyone will be able to use Chaquopy to build the
app by adding the following line to the project's `local.properties` file::

    chaquopy.license=
