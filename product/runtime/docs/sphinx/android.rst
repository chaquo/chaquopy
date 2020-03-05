.. highlight:: groovy

Android
#######

Chaquopy is distributed as a plugin for Android's Gradle-based build system.

Prerequisites:

* Android Gradle plugin version should be between 3.2 and 3.6. This is specified as
  `com.android.tools.build:gradle` in your project's top-level `build.gradle` file, and will
  usually be the same as your Android Studio version.

  Older versions as far back as 2.2 are supported by older versions of Chaquopy: see :doc:`this
  page <../versions>`. Newer versions may also work, but have not been tested with this version
  of Chaquopy.

.. (extra space for consistency)

* `minSdkVersion <https://developer.android.com/guide/topics/manifest/uses-sdk-element>`_ must
  be at least 16. Older versions as far back as 15 are supported by older versions of
  Chaquopy: see :doc:`this page <../versions>`.


Basic setup
===========

Gradle plugin
-------------

In the project's *top-level* `build.gradle` file, add the Chaquopy Maven repository and
dependency to the end of the existing `repositories` and `dependencies` blocks:

.. parsed-literal::
    buildscript {
        repositories {
            ...
            maven { url "https://chaquo.com/maven" }
        }
        dependencies {
            ...
            classpath "com.chaquo.python:gradle:|release|"
        }
    }

Then, in the *module-level* `build.gradle` file (usually in the `app` directory), apply the
Chaquopy plugin at the top of the file, but *after* the Android plugin::

   apply plugin: 'com.android.application'
   apply plugin: 'com.chaquo.python'        // Add this line

All other configuration will be done in this module-level `build.gradle`. The examples below
will show the configuration within `defaultConfig`, but it can also be done within a `product
flavor <https://developer.android.com/studio/build/build-variants#product-flavors>`_.

ABI selection
-------------

The Python interpreter is a native component, so you must use the `abiFilters
<https://google.github.io/android-gradle-dsl/current/com.android.build.gradle.internal.dsl.NdkOptions.html#com.android.build.gradle.internal.dsl.NdkOptions:abiFilters>`_
setting to specify which ABIs you want the app to support. The currently available ABIs are:

* `armeabi-v7a`, supported by virtually all Android devices.
* `arm64-v8a`, supported by most recent Android devices.
* `x86`, for the Android emulator.
* `x86_64`, for the Android emulator.

During development you will probably want to enable ABIs for both the emulator and your
devices, e.g.::

    defaultConfig {
        ndk {
           abiFilters "armeabi-v7a", "x86"
        }
    }

You may see the warning "Compatible side by side NDK version was not found". This is harmless,
and there's no need to actually install the NDK, as all of Chaquopy's native libraries are
already pre-compiled and stripped. However, you can silence the warning as follows:

* Go to Tools > SDK Manager.
* Select the SDK Tools tab.
* Select "Show Package Details".
* Under "NDK (Side by side)", select the version mentioned in the warning.

.. note:: Each ABI will add several MB to the size of the app, plus the size of any native
          :ref:`requirements <android-requirements>`. Because of the way the native components
          are packaged, the `split APK
          <https://developer.android.com/studio/build/configure-apk-splits.html>`_ and `app
          bundle <https://developer.android.com/guide/app-bundle/>`_ features cannot currently
          mitigate this. Instead, if your multi-ABI APKs are too large, try using a `product
          flavor dimension
          <https://developer.android.com/studio/build/build-variants.html#product-flavors>`_::

              android {
                  flavorDimensions "abi"
                  productFlavors {
                      arm {
                          dimension "abi"
                          ndk { abiFilters "armeabi-v7a" }
                      }
                      x86 {
                          dimension "abi"
                          ndk { abiFilters "x86" }
                      }
                  }
              }


.. _buildPython:

Development
===========

Some features require Python 3.5 or later to be available on the build machine. Chaquopy will
try to find it with the standard command for your operating system, first with a matching minor
version, and then with a matching major version.

For example, if :doc:`Chaquopy's own Python version <../versions>` is 3.8.1, then on Linux and
Mac it will first try `python3.8`, then `python3`. On Windows, it will first try `py -3.8`,
then `py -3`.

To use a different copy of Python, set its command using the `buildPython` setting. For
example, on Windows you might use one of the following::

      defaultConfig {
          python {
              buildPython "C:/Python36/python.exe"
              buildPython "py -3.7"
          }
      }

.. _android-source:

Source code
-----------

By default, Chaquopy will look for Python source code in the `python` subdirectory of each
`source set <https://developer.android.com/studio/build/index.html#sourcesets>`_. For example,
the Python code for the `main` source set should go in `src/main/python`.

To add or change source directories, use the `android.sourceSets
<https://developer.android.com/studio/build/build-variants.html#configure-sourcesets>`_ block.
For example::

    android {
        sourceSets {
            main {
                python {
                    srcDirs = ["replacement/dir"]
                    srcDir "additional/dir"
                }
            }
        }
    }

.. note:: The `setRoot
          <https://google.github.io/android-gradle-dsl/current/com.android.build.gradle.api.AndroidSourceSet.html#com.android.build.gradle.api.AndroidSourceSet:setRoot(java.lang.String)>`_
          method only takes effect on the standard Android directories. If you want to set the
          Python directory as well, you must do so explicitly, e.g.::

              main {
                  setRoot "some/other/main"
                  python.srcDirs = ["some/other/main/python"]
              }

`As with Java
<https://developer.android.com/studio/build/build-variants.html#sourceset-build>`_, it is
usually an error if the source directories for a given build variant include multiple copies of
the same filename. This is only permitted if the duplicate files are all empty, such as may
happen with `__init__.py`.

.. _android-startup:

Startup
-------

It's important to structure the app so that `Python.start()
<java/com/chaquo/python/Python.html#start-com.chaquo.python.Python.Platform->`_ is always
called with an `AndroidPlatform <java/com/chaquo/python/android/AndroidPlatform.html>`_ before
attempting to run Python code. There are two basic ways to achieve this:

* If the app always uses Python, then call Python.start() from a location which is guaranteed to run
  exactly once per process, such as `Application.onCreate()
  <https://developer.android.com/reference/android/app/Application.html#onCreate()>`_. A
  `PyApplication <java/com/chaquo/python/android/PyApplication.html>`_ subclass is provided to make
  this easy: simply add the following attribute to the `<application>` element in
  `AndroidManifest.xml`:

  .. code-block:: xml

      android:name="com.chaquo.python.android.PyApplication"

  You can also use your own subclass of `PyApplication` here.

* Alternatively, if the app only sometimes uses Python, then call Python.start() after first
  checking whether it's already been started:

  .. code-block:: java

      // "context" must be an Activity, Service or Application object from your app.
      if (! Python.isStarted()) {
          Python.start(new AndroidPlatform(context));
      }

.. _android-requirements:

Requirements
------------

.. note:: This feature requires Python on the build machine, which can be configured with the
          :ref:`buildPython <buildPython>` setting.

External Python packages may be built into the app using the `pip` block in `build.gradle`.
Within this block, add `install` lines, each specifying a package in one of the following
forms:

* A `pip requirement specifier
  <https://pip.pypa.io/en/stable/reference/pip_install/#requirement-specifiers>`_.
* A local sdist or wheel filename (relative to the project directory).
* `"-r"` followed by a local `requirements filename
  <https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format>`_ (relative
  to the project directory).

Examples::

    defaultConfig {
        python {
            pip {
                install "six"
                install "scipy==1.0.1"
                install "LocalPackage-1.2.3-py2.py3-none-any.whl"
                install "-r", "requirements.txt"
            }
        }
    }

In our most recent tests, Chaquopy could install about 90% of the top 1000 packages on `PyPI
<https://pypi.org/>`_. This includes almost all pure-Python packages, plus a constantly-growing
selection of packages with native components. To see which native packages and versions are
currently available, you can `browse the repository here <https://chaquo.com/pypi-7.0/>`_. To
request a package to be added or updated, or for any other problem with installing
requirements, please visit our `issue tracker <https://github.com/chaquo/chaquopy/issues>`_.

To pass options to `pip install`, give them as a comma-separated list to the `options` setting.
For example::

    pip {
        options "--extra-index-url", "https://example.com/private/repository"
        install "PrivatePackage==1.2.3"
    }

Any options in the `pip documentation
<https://pip.readthedocs.io/en/stable/reference/pip_install/>`_ may be used, except for those
which relate to the target environment, such as `--target`, `--user` or `-e`. If there are
multiple `options` lines, they will be combined in the order given.

.. _static-proxy-generator:

Static proxy generator
----------------------

.. note:: This feature requires Python on the build machine, which can be configured with the
          :ref:`buildPython <buildPython>` setting.

In order for a Python class to extend a Java class, or to be referenced by name in Java code or
in `AndroidManifest.xml`, a Java proxy class must be generated for it. The `staticProxy`
setting specifies which Python modules to search for these classes::

    defaultConfig {
        python {
            staticProxy "module.one", "module.two"
        }
    }

The app's :ref:`source code <android-source>` and :ref:`requirements <android-requirements>`
will be searched, in that order, for the specified modules. Either simple modules (e.g.
`module/one.py`) or packages (e.g. `module/one/__init__.py`) may be used.

Within the modules, static proxy classes must be declared using the syntax described in the
:ref:`static proxy <static-proxy>` section. For all declarations found, Java proxy classes will be
generated and built into the app.


Packaging
=========

.. _android-data:

Data files
----------

To save time and space, your app's Python modules are loaded directly from the APK assets at
runtime and don't exist as separate `.py` files. However, each module's `__file__` and
`__path__` attributes can be used in the normal way to find any data files which are packaged
along with the code. Data files in the root directory will be extracted from the APK the first
time the app is started, while files within a top-level package will be extracted the first
time that package is imported.


.. _android-bytecode:

Bytecode compilation
--------------------

Your app will start up faster if its Python code is compiled to `.pyc` format, so this is
enabled by default.

Compilation prevents source code text from appearing in stack traces, so during development you
may wish to disable it. There are individual settings for:

* `src`: :ref:`local source code <android-source>`
* `pip`: :ref:`requirements <android-requirements>`
* `stdlib`: the Python standard library

For example, to disable compilation of your local source code::

    defaultConfig {
        python {
            pyc {
                src false
            }
        }
    }

In the case of `src` and `pip`, your :ref:`buildPython <buildPython>` must use the same
bytecode format as :doc:`Chaquopy's own Python version <../versions>`. Usually this means it
must have the same minor version, e,g. if Chaquopy is using Python 3.8.1, then `buildPython`
can be any version of Python 3.8.

If the bytecode formats do not match, the build will continue with a warning, unless you've
explicitly set one of the `pyc` settings to `true`. Your app will still work, but its code will
have to be compiled on the target device, which means it will start up slower and use more
storage space.


Python standard library
=======================

.. _stdlib-unsupported:

Unsupported modules
-------------------

The following standard library modules are not currently supported:

* :any:`crypt`
* :any:`curses`
* :any:`dbm`
* :any:`grp`
* :any:`nis`
* :any:`readline`
* :any:`spwd`
* :any:`tkinter`

ssl
---

For consistency across different devices, the :any:`ssl` module is configured to use a copy of
the CA bundle from `certifi <https://github.com/certifi/python-certifi/>`_. The current version
is from certifi 2019.9.11.

sys
---

`stdout` and `stderr` are redirected to `Logcat
<https://developer.android.com/studio/debug/am-logcat.html>`_ with the tags `python.stdout` and
`python.stderr` respectively. The streams will produce one log line for each call to `write()`,
which may result in lines being split up in the log. Lines may also be split if they exceed the
Logcat message length limit of approximately 4000 bytes.

`stdin` always returns EOF. If you want to run some code which takes interactive text input, you
may find the `console app template <https://github.com/chaquo/chaquopy-console>`_ useful.


Android Studio plugin
=====================

To add Python suppport to the Android Studio user interface, you may optionally install the
JetBrains Python plugin.

.. note:: Chaquopy is not fully integrated with this plugin. It will show numerous "unresolved
          reference" warnings, and it will not support Python debugging. We hope to improve
          this in a future version.

* In Android Studio, select File > Settings.
* Go to the Plugins page, and click "Install JetBrains plugin".
* Select "Python Community Edition", and click "Install".
* Restart Android Studio when prompted.
