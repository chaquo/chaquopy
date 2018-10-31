.. highlight:: groovy

Android
#######

Chaquopy is distributed as a plugin for Android's Gradle-based build system.

Prerequisites:

* Android Gradle plugin version should be between 3.0.x and 3.2.x. This is specified as
  `com.android.tools.build:gradle` in your project's top-level `build.gradle` file, and will
  usually be the same as your Android Studio version. Newer versions may also work, but have
  not been tested with this version of Chaquopy.

  Older versions as far back as 2.2.x are supported by older versions of Chaquopy: for details,
  see :doc:`this page <../versions>`.

.. (extra space for consistency)

* `minSdkVersion <https://developer.android.com/guide/topics/manifest/uses-sdk-element>`_ must
  be at least 15 (Android 4.0.3).


Basic setup
===========

.. note:: Previous versions of Chaquopy required you to specify a Python version to build into
          your app. From Chaquopy 5.x onwards, this is no longer necessary because each
          Chaquopy version comes with only one Python version. For the mapping between
          versions, see :doc:`this page <../versions>`.

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

.. _buildPython:

buildPython
-----------

Some features require Python 3.4 or later to be available on the build machine. By default,
Chaquopy will execute `python3` on Linux and Mac, or `py -3` on Windows, so if you have a
standard version of Python installed, no action should be required.

Otherwise, set the Python executable using the `buildPython` setting. For example, on Windows
you might use the following::

      defaultConfig {
          python {
              buildPython "C:/Python36/python.exe"
          }
      }


ABI selection
-------------

The Python interpreter is a native component, so you must specify which native ABIs you
want the app to support. The currently available ABIs are:

* `armeabi-v7a`, for the vast majority of Android hardware.
* `x86`, for the Android emulator.

During development you will probably want to enable them both::

    defaultConfig {
        ndk {
           abiFilters "armeabi-v7a", "x86"
        }
    }

There's no need to actually install the Android native development kit (NDK), as Chaquopy will
download pre-compiled CPython binaries for the selected ABIs.

.. note:: Each ABI will add several MB to the size of the app, plus the size of any native
          :ref:`requirements <android-requirements>`. It will also make the app take longer to
          build. Because of the way the native components are packaged, the `split APK
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

Android Studio plugin
---------------------

To add Python suppport to the Android Studio user interface, you may optionally install the
JetBrains Python plugin.

.. note:: Chaquopy is not fully integrated with this plugin. It will show numerous "unresolved
          reference" warnings, and it will not support Python debugging. We hope to improve
          this in a future version.

* In Android Studio, select File > Settings.
* Go to the Plugins page, and click "Install JetBrains plugin".
* Select "Python Community Edition", and click "Install".
* Restart Android Studio when prompted.


Development
===========

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

External Python packages may be built into the app by adding a `python.pip` block to
`build.gradle`. Within this block, add `install` lines, each specifying a package in one of the
following forms:

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
                install "six==1.10.0"
                install "scipy==1.0.1"
                install "LocalPackage-1.2.3-py2.py3-none-any.whl"
                install "-r", "requirements.txt"
            }
        }
    }

In our most recent tests, Chaquopy could install about 80% of the top 1000 packages on `PyPI
<https://pypi.org/>`_. This includes almost all pure-Python packages, plus a constantly-growing
selection of packages with native components. To see which native packages and versions are
currently available, you can `browse the repository here <https://chaquo.com/pypi-2.1/>`_. To
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

The app's :ref:`source tree <android-source>` and its :ref:`requirements
<android-requirements>` will be searched, in that order, for the specified modules. Either
simple modules (e.g. `module/one.py`) or packages (e.g. `module/one/__init__.py`) may be found.

Within the modules, static proxy classes must be declared using the syntax described in the
:ref:`static proxy <static-proxy>` section. For all declarations found, Java proxy classes will be
generated and built into the app.


Packaging
=========

.. _android-bytecode:

Bytecode compilation
--------------------

Your app will start up faster if its Python code is compiled to `.pyc` format. This is
currently only supported for the Python standard library, but may be extended to app code and
pip-installed packages in a future version.

Compilation prevents source code text from appearing in Python stack traces, so you may wish
to disable it during development. The default settings are as follows::

    defaultConfig {
        python {
            pyc {
                stdlib true
            }
        }
    }

.. _extractPackages:

Resource files
--------------

By default, Python modules are loaded directly from the APK assets at runtime and don't exist
as separate files. Because of this, any code which depends upon :any:`__file__` to locate
resource files will fail. There are two ways of dealing with this.

The most efficient way is to change the code to use :any:`pkgutil.get_data` instead. For
example, to read `package1/subdir/README.txt`:

.. code-block:: python

    from pkgutil import get_data

    # From any Python file directly within package1/:
    readme_bytes = get_data(__name__, "subdir/README.txt")

    # Or from elsewhere:
    import package1
    readme_bytes = get_data(package1.__name__, "subdir/README.txt")

    # Then, to open it like a file:
    import io
    readme_file = io.StringIO(readme_bytes.decode())

Alternatively, you can specify certain Python packages to extract at runtime using the
`extractPackages` setting. For example::

    defaultConfig {
        python {
            extractPackages "package1"
        }
    }

Then you can use :any:`__file__` in the normal way:

.. code-block:: python

    from os.path import dirname, join

    # From any Python file directly within package1/:
    readme_file = open(join(dirname(__file__), "subdir/README.txt"))

    # Or from elsewhere:
    import package1
    readme_file = open(join(dirname(package1.__file__), "subdir/README.txt"))

Extracted packages will load slower and use more storage space, so you should extract the
deepest possible package which contains both the module on which `__file__` is looked up, and
the files being loaded.

`extractPackages` is used by default for certain PyPI packages which are known to require it.
If you discover any more, please `let us know <https://github.com/chaquo/chaquopy/issues>`_.


Python standard library
=======================

ssl
---

Because of inconsistencies in the system certificate authority store formats of different Android
versions, the `ssl` module is configured to use a copy of the CA bundle from `certifi
<https://github.com/certifi/python-certifi/>`_. The current version is from certifi 2018.01.18.

sys
---

`stdout` and `stderr` are redirected to `Logcat
<https://developer.android.com/studio/debug/am-logcat.html>`_ with the tags `python.stdout` and
`python.stderr` respectively. The streams will produce one log line for each call to `write()`,
which may result in lines being split up in the log. Lines may also be split if they exceed the
Logcat message length limit of approximately 4000 bytes.

`stdin` always returns EOF. If you want to run some code which takes interactive text input, you
may find the `console app template <https://github.com/chaquo/chaquopy-console>`_ useful.


Licensing
=========

Evaluation
----------

You can try out Chaquopy right now by cloning one of the :ref:`example apps <quick-start>`, or
following the setup instructions above in an app of your own.

An unlicensed SDK is fully-functional, but apps built with it will display a notification on
startup, and are limited to a run-time of 5 minutes. To remove these restrictions, a license is
required. All licenses are perpetual and include upgrades to all future versions.

Once you have a license key, activate it by adding the following line to the project’s
`local.properties` file::

    chaquopy.license=<license key>

Standard license
----------------

A standard license allows unlimited use of Chaquopy in any number of apps. Please `contact us
<https://chaquo.com/chaquopy/contact/>`_ to request a license key, giving the following information:

* A summary of what your app is, and how Chaquopy will be used in it.
* How many developers on your project will be using Chaquopy.

Open-source license
-------------------

For open-source apps, Chaquopy will always be free of charge. Please `contact us
<https://chaquo.com/chaquopy/contact/>`_ with details of your app, including:

* The `applicationId <https://developer.android.com/studio/build/application-id>`_ from your
  `build.gradle`.
* Where the app is distributed (e.g. Google Play).
* Where the app's source code is available.
