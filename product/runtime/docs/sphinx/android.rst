.. highlight:: groovy

Android
#######

Chaquopy is distributed as a plugin for Android's Gradle-based build system. For a full example of
how to use it, see the `demo app <https://github.com/chaquo/chaquopy>`_.

Prerequisites:

* Android Gradle plugin version 2.2, 2.3 or 3.0. (This is specified as
  `com.android.tools.build:gradle` in your project's top-level `build.gradle` file, and will
  usually be the same as your Android Studio version.)
* `minSdkVersion` 15 or higher.

Basic setup
===========

In the project's *top-level* `build.gradle` file, add the following lines to the existing
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

In the app's *module-level* `build.gradle` file, apply the Chaquopy plugin at the top of the
file, but after the Android plugin::

   apply plugin: "com.chaquo.python"  // Must come after com.android.application

Chaquopy is configured in the `python` block within `defaultConfig`. The only required setting
is the Python version, and currently the only available version is 2.7.10::

    android {
        defaultConfig {
            python {
               version "2.7.10"
            }
        }
    }

The Python interpreter is a native component, so you must specify which native ABIs you want
the app to support. The currently available ABIs are:

* `armeabi-v7a`, for the vast majority of Android hardware.
* `x86`, for the Android emulator.

During development you will probably want to enable them both::

    android {
        defaultConfig {
            ndk {
               abiFilters "armeabi-v7a", "x86"
            }
        }
    }

There's no need to actually install the Android native development kit (NDK), as Chaquopy will
download pre-compiled CPython binaries for the specified ABIs. (Each ABI will add several MB to
the size of the app.)

.. _android-development:

Development
===========

Place Python source code in `src/main/python`, and Chaquopy will automatically build it into
the app.

It's important to structure the app so that `Python.start()
<java/com/chaquo/python/Python.html#start-com.chaquo.python.Python.Platform->`_ is always
called with an `AndroidPlatform <java/com/chaquo/python/android/AndroidPlatform.html>`_ before
attempting to run Python code. There are two basic ways to achieve this:

If the app always uses Python, then call Python.start() from a location which is guaranteed to
run exactly once per process. The recommended location is `Application.onCreate()
<https://developer.android.com/reference/android/app/Application.html#onCreate()>`_, and a
`PyApplication <java/com/chaquo/python/android/PyApplication.html>`_ subclass is provided to
make this easy. To use it, simply add the following attribute to the `<application>` element in
`AndroidManifest.xml`:

.. code-block:: xml

    android:name="com.chaquo.python.android.PyApplication"

Alternatively, if the app only sometimes uses Python, then call Python.start() after first
checking whether it's already been started:

.. code-block:: java

    // "context" must be an Activity, Service or Application object from your app.
    if (! Python.isStarted()) {
        Python.start(new AndroidPlatform(context));
    }

Other build features
====================

These features all require Python 2.7 to be available on the build machine. Chaquopy will by
default look for `python2` on your `PATH`, but this can be configured with the `buildPython`
setting. For example, a typical Windows installation of Python would look like this::

    python {
        buildPython "C:/Python27/python.exe"
    }

.. _android-requirements:

Python requirements
-------------------

External Python packages may be built into the app by adding `install` lines within the
`python.pip` block. Each line should specify a requirement in one of the following forms:

* A `pip requirement specifier
  <https://pip.pypa.io/en/stable/reference/pip_install/#requirement-specifiers>`_.
* A local wheel filename (relative to the project directory).
* `"-r"` followed by a local `requirements filename
  <https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format>`_ (relative
  to the project directory).

Examples::

    python {
        pip {
            install "six==1.10.0"
            install "LocalPackage-1.2.3-py2.py3-none-any.whl"
            install "-r", "requirements.txt"
        }
    }

.. note:: Chaquopy can only install wheel files, not sdist packages. As well as `PyPI
          <https://pypi.python.org/pypi>`_, Chaquopy also searches for wheels in its own
          package repository, which contains Android builds of certain native packages, as well
          as pure-Python packages which aren't available from PyPI in wheel format.

          To see which packages and versions are currently available, you can `browse the
          repository here <https://chaquo.com/pypi/>`_. To request a package to be added or
          updated, please visit our `issue tracker
          <https://github.com/chaquo/chaquopy/issues>`_.

To pass options to `pip install
<https://pip.readthedocs.io/en/stable/reference/pip_install/>`_, give them as a comma-separated
list to the `python.pip.options` property. For example::

    python {
        pip {
            options "--extra-index-url", "https://example.com/private/repository"
            install "PrivatePackage==1.2,3"
        }
    }

Any `pip install` options may be specified, except the following:

* Target environment options, such as `--target` and `--user`.
* Installation format options, such as `-e` and `--egg`.
* Package type options, such as `--no-binary`.

.. _static-proxy-generator:

Static proxy generator
----------------------

In order for a Python class to extend a Java class, or to be referenced by name in Java code or
in `AndroidManifest.xml`, a Java proxy class must be generated for it. The `staticProxy`
setting specifies which Python modules to search for these classes::

    python {
        staticProxy "module.one", "module.two"
    }

The app's :ref:`source tree <android-development>` and its :ref:`requirements
<android-requirements>` will be searched, in that order, for the specified modules. Either
simple modules (e.g. `module/one.py`) or packages (e.g. `module/one/__init__.py`) may be used.

Within the modules, static proxy classes must be declared in the format described in the
:ref:`static proxy <static-proxy>` section. For all declarations found, Java proxy classes will be
generated and built into the app.

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
