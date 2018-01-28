.. highlight:: groovy

Android
#######

Chaquopy is distributed as a plugin for Android's Gradle-based build system.

Prerequisites:

* Android Gradle plugin version 2.2, 2.3 or 3.0. (This is specified as
  `com.android.tools.build:gradle` in your project's top-level `build.gradle` file, and will
  usually be the same as your Android Studio version.)
* `minSdkVersion` 15 or higher.
* Some features require a Python interpreter (version 2.7 or 3.3+) to be available on the build
  machine. Chaquopy will by default look for `python` on your `PATH`, but this can be
  configured with the `buildPython` setting. For example, a typical Windows installation of
  Python would look like this::

      python {
          buildPython "C:/Python27/python.exe"
      }

Basic setup
===========

For a minimal example, see `chaquopy-hello <https://github.com/chaquo/chaquopy-hello>`_, a
Python version of the Android Studio "Empty Activity" app template. For a more complete
example, see the `demo app <https://github.com/chaquo/chaquopy>`_.

Plugin
------

In the project's *top-level* `build.gradle` file, add the Chaquopy repository and dependency to
the end of the existing `repositories` and `dependencies` blocks:

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

In the app's *module-level* `build.gradle` file, apply the Chaquopy plugin at the top of the
file, but *after* the Android plugin::

   apply plugin: "com.chaquo.python"    // Must come after com.android.application

Python version
--------------

With the plugin applied, you can now add a `python` block within `android.defaultConfig`. The
only required setting in this block is the Python version, and the currently available versions
are:

* 2.7.14
* 3.6.3

For example::

    defaultConfig {
        python {
            version "3.6.3"
        }
    }

.. note:: The following obsolete versions are still available, but should not be used for new
          projects:

          * 2.7.10

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

.. note:: Each ABI will add several MB to the size of the app. Because some of the native
          components are stored as assets, the `split APK
          <https://developer.android.com/studio/build/configure-apk-splits.html>`_ feature
          cannot be used to mitigate this. If you want to build separate APKs for each ABI,
          this can instead be done using a `product flavor dimension
          <https://developer.android.com/studio/build/build-variants.html#product-flavors>`_::

              android {
                  flavorDimensions "abi"
                  productFlavors {
                      armeabi_v7a {
                          dimension "abi"
                          ndk { abiFilters "armeabi-v7a" }
                      }
                      x86 {
                          dimension "abi"
                          ndk { abiFilters "x86" }
                      }
                  }
              }

.. _android-development:

Development
===========

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


Startup
-------

It's important to structure the app so that `Python.start()
<java/com/chaquo/python/Python.html#start-com.chaquo.python.Python.Platform->`_ is always
called with an `AndroidPlatform <java/com/chaquo/python/android/AndroidPlatform.html>`_ before
attempting to run Python code. There are two basic ways to achieve this:

* If the app always uses Python, then call Python.start() from a location which is guaranteed to
  run exactly once per process. The recommended location is `Application.onCreate()
  <https://developer.android.com/reference/android/app/Application.html#onCreate()>`_, and a
  `PyApplication <java/com/chaquo/python/android/PyApplication.html>`_ subclass is provided to
  make this easy. To use it, simply add the following attribute to the `<application>` element in
  `AndroidManifest.xml`:

  .. code-block:: xml

      android:name="com.chaquo.python.android.PyApplication"

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

External Python packages may be built into the app by adding a `python.pip` block to
`build.gradle`. Within this block, add `install` lines, each specifying a package in one of the
following forms:

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
list to the `options` property. For example::

    python {
        pip {
            options "--extra-index-url", "https://example.com/private/repository"
            install "PrivatePackage==1.2.3"
        }
    }

There may be multiple `options` lines: the options will be combined in the order given. Any
`pip install` options may be used, except the following:

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
simple modules (e.g. `module/one.py`) or packages (e.g. `module/one/__init__.py`) may be found.

Within the modules, static proxy classes must be declared using the syntax described in the
:ref:`static proxy <static-proxy>` section. For all declarations found, Java proxy classes will be
generated and built into the app.

Packaging
=========

Bytecode compilation
--------------------

Your app will start up faster if its Python code is compiled to `.pyc` format. This is
currently only supported for the Python standard library, but may be extended to app code and
pip-installed packages in a future version.

Compilation prevents source code text from appearing in Python stack traces, so you may wish
to disable it during development. The default settings are as follows::

    python {
        pyc {
            stdlib true
        }
    }

Resource files
--------------

By default, Python modules are loaded directly from the APK assets at runtime and don't exist
as separate files. Because of this, any code which depends upon :any:`__file__` to locate
resource files will fail. There are two ways of dealing with this.

The most efficient way is to change the code to use :any:`pkgutil.get_data` instead. For
example, to load `some/package/subdir/README.txt` from within `some/package/module.py`:

.. code-block:: python

    readme = pkgutil.get_data(__name__, "subdir/README.txt")
    # To read it like a file, use io.StringIO(readme.decode())

If this is not feasible (e.g. if the code is installed :ref:`using pip
<android-requirements>`), then you can specify certain Python packages to extract at runtime
using the `extractPackages` setting. For example::

    python {
        extractPackages "somepackage", "some.subpackage"
    }

Extracted packages will load slower and use more storage space, so you should specify the
deepest possible package which contains both the module on which `__file__` is looked up, and
the files being loaded.

`extractPackages` is used by default for certain PyPI packages which are known to require it.
If you discover any more, please `let us know <https://github.com/chaquo/chaquopy/issues>`_.

Licensing
=========

Evaluation
----------

You can try out Chaquopy right now by cloning one of the `example apps
<https://github.com/chaquo>`_, or following the setup instructions above in an app of your own.
The unlicensed version is fully-functional, but apps built with it will display a notification
on startup.

In order to distribute apps built with Chaquopy, a license is required. All licenses are
perpetual and include upgrades to all future versions.

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
