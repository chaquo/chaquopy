:tocdepth: 2

Change log
##########

.. towncrier release notes start

15.0.1 (2023-12-24)
===================

Features
--------

- Kotlin build.gradle.kts files are now supported. (`#231
  <https://github.com/chaquo/chaquopy/issues/231>`__)
- A new Gradle DSL has been added, with a top-level `chaquopy` block. Kotlin
  build.gradle.kts files must use the new DSL; Groovy build.gradle files may
  use either the new or the old one. (`#231
  <https://github.com/chaquo/chaquopy/issues/231>`__)
- All Android wheels are now downloaded from https://chaquo.com/pypi-13.1/ –
  the old pypi-7.0 URL is no longer used. (`#808
  <https://github.com/chaquo/chaquopy/issues/808>`__)
- `os.get_terminal_size` now returns ENOTTY rather than EPERM, which was
  causing avc log spam when stdio is redirected. (`#886
  <https://github.com/chaquo/chaquopy/issues/886>`__)
- Update CA bundle to certifi 2023.11.17. (`#893
  <https://github.com/chaquo/chaquopy/issues/893>`__)
- Android Gradle plugin versions 8.1 to 8.5 are now supported. (`#908
  <https://github.com/chaquo/chaquopy/issues/908>`__, `#1003
  <https://github.com/chaquo/chaquopy/issues/1003>`__, `#1091
  <https://github.com/chaquo/chaquopy/issues/1091>`__, `#1140
  <https://github.com/chaquo/chaquopy/issues/1140>`__, `#1172
  <https://github.com/chaquo/chaquopy/issues/1172>`__)
- Python version 3.12 is now supported. (`#931
  <https://github.com/chaquo/chaquopy/issues/931>`__, `#967
  <https://github.com/chaquo/chaquopy/issues/967>`__)
- Update runtime Python versions to 3.8.18, 3.9.18, 3.10.13, 3.11.6, and
  3.12.1. (`#932 <https://github.com/chaquo/chaquopy/issues/932>`__)
- The `importlib.resources.files` API is now supported in Python 3.9 and later.
  (`#977 <https://github.com/chaquo/chaquopy/issues/977>`__)
- Update pkg_resources from setuptools version 68.2.2.


Deprecations and Removals
-------------------------

- The 32-bit ABIs `armeabi-v7a` and `x86` will no longer be supported on Python
  3.12 and later. (`#709 <https://github.com/chaquo/chaquopy/issues/709>`__)
- Android Gradle plugin versions 4.1 and 4.2 are no longer supported. (`#787
  <https://github.com/chaquo/chaquopy/issues/787>`__, `#840
  <https://github.com/chaquo/chaquopy/issues/840>`__)


Bugfixes
--------

- Fix "AttributeError: "'AssetFinder' object has no attribute
  'extract_packages'" when AssetFinder subdirectories are on `sys.path`.
  (`#820 <https://github.com/chaquo/chaquopy/issues/820>`__)
- Unsupported `socket` functions such as `if_nametoindex` now throw `OSError`
  as documented, rather than `AttributeError`. (`#870
  <https://github.com/chaquo/chaquopy/issues/870>`__)
- Fix FileNotFoundError when `pkgutil.iter_modules` is called with a
  nonexistent path. (`#917 <https://github.com/chaquo/chaquopy/issues/917>`__)
- ZIP files using BZ2 or LZMA compression are now supported. (`#953
  <https://github.com/chaquo/chaquopy/issues/953>`__)


14.0.2 (2023-01-29)
===================

Features
--------

- `sys.stdout` and `sys.stderr` are now line-buffered by default. (`#654
  <https://github.com/chaquo/chaquopy/issues/654>`__, `#746
  <https://github.com/chaquo/chaquopy/issues/746>`__, `#757
  <https://github.com/chaquo/chaquopy/issues/757>`__)
- Add option to `redirect native stdout and stderr to Logcat
  <java/com/chaquo/python/android/AndroidPlatform.html#redirectStdioToLogcat-->`__.
  (`#725 <https://github.com/chaquo/chaquopy/issues/725>`__)
- Update to Python version 3.8.16 and OpenSSL version 1.1.1s. This fixes the
  Google Play warning "Your app uses a defective version of the OpenSSL
  library". (`#727 <https://github.com/chaquo/chaquopy/issues/727>`__)
- Update CA bundle to certifi 2022.12.7. (`#747
  <https://github.com/chaquo/chaquopy/issues/747>`__)
- Add `python` executable as a final fallback when searching for buildPython.
  (`#752 <https://github.com/chaquo/chaquopy/issues/752>`__)
- Restore the `extractPackages` setting, for code that requires its modules to
  exist as separate .py files. (`#754
  <https://github.com/chaquo/chaquopy/issues/754>`__)
- Android Gradle plugin version 7.4 is now supported. (`#756
  <https://github.com/chaquo/chaquopy/issues/756>`__)
- Android Gradle plugin version 8.0 is now supported, though projects which use
  `minifyEnabled true` will need a workaround. (`#842
  <https://github.com/chaquo/chaquopy/issues/842>`__)
- Update to pip version 20.1.


Deprecations and Removals
-------------------------

- :ref:`buildPython` must now be at least Python 3.7. (`#713
  <https://github.com/chaquo/chaquopy/issues/713>`__)


Bugfixes
--------

- Enable PEP 517 builds in pip. (`#715
  <https://github.com/chaquo/chaquopy/issues/715>`__)
- Show correct error message when buildPython autodetection fails. (`#733
  <https://github.com/chaquo/chaquopy/issues/733>`__)
- Fix error when calling `entry_points` with an unreadable directory on
  `sys.path`. (`#755 <https://github.com/chaquo/chaquopy/issues/755>`__)
- Fix "Could not find an activated virtualenv" error when
  `PIP_REQUIRE_VIRTUALENV` environment variable is set. (`#777
  <https://github.com/chaquo/chaquopy/issues/777>`__)


13.0.0 (2022-11-06)
===================

* Android Gradle plugin version 7.3 is now supported (`#663
  <https://github.com/chaquo/chaquopy/issues/663>`_).
* [**BACKWARD INCOMPATIBLE**] `minSdkVersion` must now be at least API level 21. This
  still covers `98% of active devices
  <https://dl.google.com/android/studio/metadata/distributions.json>`_.
* Python versions 3.9, 3.10 and 3.11 are now supported (`#661
  <https://github.com/chaquo/chaquopy/issues/661>`_).
* Detect changes to files or directories listed in requirements files (`#660
  <https://github.com/chaquo/chaquopy/issues/660>`_).
* Projects are no longer required to have a local.properties file, as long as the
  `ANDROID_HOME` or `ANDROID_SDK_ROOT` environment variable is set (`#672
  <https://github.com/chaquo/chaquopy/issues/672>`_).
* Enable all warnings, including :any:`DeprecationWarning`,
  :any:`PendingDeprecationWarning`, :any:`ImportWarning` and :any:`ResourceWarning`.
* Update pkg_resources from setuptools version 56.2.0.
* Update to SQLite version 3.39.2.
* Update Python 3.9 and later to OpenSSL version 3.0.5.

12.0.1 (2022-07-24)
===================

* First open-source release. Apart from removing the license restrictions, this is
  identical to version 12.0.0.

12.0.0 (2022-05-12)
===================

* Android Gradle plugin version 7.2 is now supported (`#613
  <https://github.com/chaquo/chaquopy/issues/613>`_).
* [**BACKWARD INCOMPATIBLE**] Android Gradle plugin version 4.0 is no longer supported.
* Update to Python version 3.8.13 (see `its changelog
  <https://docs.python.org/3.8/whatsnew/changelog.html>`__ for details).
* Update CA bundle to certifi 2021.10.8.
* Fix :any:`signal.valid_signals` on 32-bit ABIs (`#600
  <https://github.com/chaquo/chaquopy/issues/600>`_).
* Allow `buildscript` configuration to be in a subproject (`#615
  <https://github.com/chaquo/chaquopy/issues/615>`_).

11.0.0 (2022-02-01)
===================

* Android Gradle plugin version 7.1 is now supported.
* [**BACKWARD INCOMPATIBLE**] Android Gradle plugin version 3.6 is no longer supported.
* Remove warning about untested Android Gradle plugin versions, as they are usually backward
  compatible.
* Gradle `pluginManagement` and `plugins` syntax is now supported.
* Java arrays now support the :any:`copy.copy` function in Python.
* Passing an unsupported Java object to :any:`copy.copy`, :any:`copy.deepcopy` or :any:`pickle`
  now fails with a clearer error message.

10.0.1 (2021-09-22)
===================

* Android Gradle plugin versions 4.2 and 7.0 are now supported.
* [**BACKWARD INCOMPATIBLE**] Android Gradle plugin versions 3.4 and 3.5 are no longer
  supported.
* [**BACKWARD INCOMPATIBLE**] The `version` setting is no longer supported. Simply remove it to
  use the current version of Python.
* Update to Python version 3.8.11 (see `its changelog
  <https://docs.python.org/3.8/whatsnew/changelog.html>`__ for details).
* Update to pip version 19.2.3 (see `its changelog <https://pip.pypa.io/en/stable/news/>`__ for
  details).
* Update CA bundle to certifi 2021.5.30.
* Add a `buffer` attribute to stdout and stderr for bytes output (`#464
  <https://github.com/chaquo/chaquopy/issues/464>`_, `#516
  <https://github.com/chaquo/chaquopy/issues/516>`_).
* Java arrays now support the `index` and `count` methods in Python. In order to support code
  with `hasattr` checks, they also now implement the methods `__contains__`, `__iter__` and
  `__reversed__`, rather than relying on the fallback to `__getitem__` (`#306
  <https://github.com/chaquo/chaquopy/issues/306>`_).
* Fix "truth value of an array with more than one element is ambiguous" error when passing a
  NumPy array to a method which takes a Java array (`#526
  <https://github.com/chaquo/chaquopy/issues/526>`_).
* NumPy integer scalars, and anything else which implements the `__index__` method, can now be
  used as a Java array index (`#495 <https://github.com/chaquo/chaquopy/issues/495>`_).
* Add workaround to help conda Python on Windows find its SSL libraries (`#450
  <https://github.com/chaquo/chaquopy/issues/450>`_).
* Fix "invalid literal for int" error in pip_install when project path includes a symlink
  (`#468 <https://github.com/chaquo/chaquopy/issues/468>`_).
* Fix crash caused by empty files in the APK on Android 7 (`Electron Cash #2136
  <https://github.com/Electron-Cash/Electron-Cash/issues/2136>`_).
* :any:`importlib.util.spec_from_file_location` now works for paths loaded from the APK.

9.1.0 (2021-01-02)
==================

* Fix error "'HTMLParser' object has no attribute 'unescape'" on Python 3.9 (`#416
  <https://github.com/chaquo/chaquopy/issues/416>`_).
* Fix error "must supply either home or prefix/exec-prefix -- not both" on Homebrew for Mac
  (`#405 <https://github.com/chaquo/chaquopy/issues/405>`_).
* `buildPython` path can now contain spaces.
* Java API is now annotated with `@NotNull` where appropriate.
* Java arrays now support the `copy` method in Python.
* Fix bug when using `cast` to call a functional interface which extends another functional
  interface.
* Update CA bundle to certifi 2020.12.5.
* :any:`json` module performance improvements.
* Java API performance improvements.

9.0.0 (2020-11-06)
==================

* Android Gradle plugin version 4.1 is now supported.
* [**BACKWARD INCOMPATIBLE**] Android Gradle plugin version 3.3 is no longer supported.
* Update to Python version 3.8.6 (see `its changelog
  <https://docs.python.org/3.8/whatsnew/changelog.html>`__ for details).
* Java/Kotlin objects implementing functional interfaces can now be called from Python using
  `()` syntax. This includes lambdas, method references, and any interface with a single
  abstract method, such as `java.lang.Runnable`.
* Java arrays can now be accessed from Python using negative indices and slice syntax.
* Fix conversion of non-contiguous NumPy arrays to Java arrays.
* Remove inaccessible directories from :any:`os.get_exec_path` (`#346
  <https://github.com/chaquo/chaquopy/issues/346>`_).
* Make :any:`zipimport` implement the new loader API. This affected the package `dateparser`.
* If `bdist_wheel` fails for an unknown reason, fall back on `setup.py install`. This affected
  the packages `acoustics` and `kiteconnect` (`#338
  <https://github.com/chaquo/chaquopy/issues/338>`_).
* Fix `ClassNotFoundException` when `minifyEnabled` is in use (`#261
  <https://github.com/chaquo/chaquopy/issues/261>`_).

8.0.1 (2020-07-28)
==================

* Make missing :any:`multiprocessing` primitives throw an exception on use rather than on
  import. This affected the packages `joblib` and `librosa` (`#21
  <https://github.com/chaquo/chaquopy/issues/21>`_).
* Make :any:`ctypes.util.find_library` search libraries installed with pip. This affected the
  package `soundfile` (`#201 <https://github.com/chaquo/chaquopy/issues/201>`_).
* Fix "invalid constraint" error affecting the packages `openpyxl` and `webcolors`.

8.0.0 (2020-06-15)
==================

* Android Gradle plugin version 4.0 is now supported.
* [**BACKWARD INCOMPATIBLE**] Android Gradle plugin version 3.2 is no longer supported.
* Update to Python version 3.8.3 (see `its changelog
  <https://docs.python.org/3.8/whatsnew/changelog.html>`__ for details).
* Using Chaquopy in an Android library module (AAR) is now supported (`#94
  <https://github.com/chaquo/chaquopy/issues/94>`_).
* Java primitive arrays now support the Python buffer protocol, allowing high-performance data
  transfer between the two languages.
* Data files in top-level non-package directories are now extracted from the APK the first time
  the app is started, so they can be accessed using a path relative to `__file__`.

7.0.3 (2020-05-11)
==================

* Fix `"This platform lacks a functioning sem_open implementation"
  <https://stackoverflow.com/questions/61089650>`_ error when using
  `multiprocessing.dummy.Pool` (aka `multiprocessing.pool.ThreadPool`). This affected many
  common uses of TensorFlow.
* Work around dynamic linker bug on 64-bit ABIs before API level 23 (`#228
  <https://github.com/chaquo/chaquopy/issues/228>`_).
* Fix `out of memory error <https://stackoverflow.com/questions/60919031>`_ when running Gradle
  with a small heap size.
* Fix incompatibility with external package `importlib_metadata` (`#276
  <https://github.com/chaquo/chaquopy/issues/276>`_).
* Fix `NoClassDefFoundError` when using Python to access certain `androidx` classes, including
  `AppCompatTextView`.
* Fix conversion of Java `byte[]` array to Python :any:`bytearray`.
* Improve startup speed by deferring `pkg_resources` initialization until the module is first
  imported.
* Update CA bundle to certifi 2020.4.5.1.

7.0.2 (2020-03-05)
==================

* [**BACKWARD INCOMPATIBLE**] Update to Python version 3.8.1 (see the `3.7
  <https://docs.python.org/3/whatsnew/3.7.html>`_ and `3.8
  <https://docs.python.org/3/whatsnew/3.8.html>`_ release notes for details).

  * All Python standard library modules are now supported except those in :ref:`this list
    <stdlib-unsupported>`. In particular, support has been added for :any:`bz2`,
    `importlib.metadata`, :any:`importlib.resources` and :any:`lzma`.
  * Most native packages have been upgraded to a more recent version. If you've used specific
    version numbers in a `build.gradle` or `requirements.txt` file, you may need to update
    them. See `the repository index <https://chaquo.com/pypi-7.0/>`_ for a complete list.
* Android Gradle plugin version 3.6 is now supported.
* [**BACKWARD INCOMPATIBLE**] Android Gradle plugin version 3.1 is no longer supported.
* [**BACKWARD INCOMPATIBLE**] :ref:`buildPython <buildPython>` must now be at least Python 3.5.
* Expose Java API using `api` configuration so it's available to dynamic feature modules.
* Update CA bundle to certifi 2019.9.11.
* Fix "cannot create a consistent method resolution order" error when using `androidx`.
* Fix a deadlock involving the Java API.
* Improve local caching of packages which aren't available as wheels.
* Reduce some temporary filename lengths to avoid the Windows 260-character limit.
* Improve startup speed.

6.3.0 (2019-08-25)
==================

* Android Gradle plugin version 3.5 is now supported.
* Pre-compile Python code to `.pyc` format by default, so it doesn't have to be compiled on the
  device. This significantly improves app startup speed and storage usage.
* Remove the `extractPackages` setting, as data files are now extracted automatically. See
  :ref:`the documentation <android-data>` for details.
* Change data file location from cache to files directory, to prevent the user from clearing it
  while the app is running.
* Hide importer frames in stack traces, unless the exception originated from the importer
  itself.
* Fix another metadata parsing issue, this one affecting the package `astroid`.
* Fix "has no DT_SONAME" warning (`#112 <https://github.com/chaquo/chaquopy/issues/112>`_).

6.2.1 (2019-04-19)
==================

* Android Gradle plugin version 3.4 is now supported.
* Update to OpenSSL 1.1.1b. This enables the BLAKE2 and SHA-3 algorithms in `hashlib`.
* Update CA bundle to certifi 2019.3.9.
* Implement `pkgutil.iter_modules`.
* Build `pkg_resources` into all apps. Many packages require this but don't declare a
  dependency on setuptools.

6.0.0 (2019-03-08)
==================

* Android Gradle plugin version 3.3 is now supported.
* [**BACKWARD INCOMPATIBLE**] Android Gradle plugin version 3.0 is no longer supported.
* The ABI `x86_64` is now supported.

5.1.2 (2019-01-19)
==================

* Add `PyObject` primitive conversion methods (`toBoolean`, `toInt`, etc.).
* Add `PyObject` container view methods (`asList`, `asMap` and `asSet`).
* If `pkg_resources` is installed in your app, its `"basic resource access"
  <https://setuptools.readthedocs.io/en/latest/pkg_resources.html#basic-resource-access>`_
  functions will now work.
* Remove directory names when converting exception stack traces from Python to Java. This works
  around a bug in Google Play which was causing crash reports to be incomplete.
* Change default character encoding from ASCII to UTF-8.
* Make APK build more reproducible.

5.0.0 (2018-11-05)
==================

* The ABI `arm64-v8a` is now supported.
* [**BACKWARD INCOMPATIBLE**] Each Chaquopy version will now include only one Python version,
  so the `version` setting is no longer required. Simply remove it to use the current
  version, 3.6.5.

  * Python 2 is no longer included. However, for existing Python 2 users, Chaquopy 4.x will
    continue to be maintained until the end of 2019 (`#39
    <https://github.com/chaquo/chaquopy/issues/39>`_).

* [**BACKWARD INCOMPATIBLE**] :ref:`buildPython <buildPython>` must now be at least Python 3.4.
* [**BACKWARD INCOMPATIBLE**] `minSdkVersion` must now be at least API level 16. This still
  covers `99% of active devices <https://developer.android.com/about/dashboards/index.html>`_.
* Runtime components are now distributed as separate Maven artifacts. This fixes various
  intermittent build errors involving `chaquopy_java.jar` (`#62
  <https://github.com/chaquo/chaquopy/issues/62>`_).
* If `pkg_resources` is installed in your app, it will now detect all pip-installed packages.

4.0.0 (2018-08-22)
==================

* Android Gradle plugin version 3.2 is now supported.
* [**BACKWARD INCOMPATIBLE**] Android Gradle plugin version 2.3 is no longer supported.
* Add :any:`resource` module.
* Remove broken :any:`select.kevent`/:any:`select.kqueue` API. This affected `PyZMQ
  <https://pypi.org/project/pyzmq/>`_, which should now work
  (Crystax issue `#1433 <https://tracker.crystax.net/issues/1433>`_).
* Set `HOME` environment variable if the system hasn't already done so, so
  :any:`os.path.expanduser` can return a usable location.
* Implement :any:`importlib.abc.InspectLoader.get_code`: this allows :any:`runpy.run_module` to
  be used.

3.3.2 (2018-08-01)
==================

* Fix pip issues involving packages with optional native components (e.g. `websockets
  <https://pypi.org/project/websockets/>`_).
* Work around inability of Android dynamic linker on API 22 and older to load multiple modules
  with the same basename (`details here <https://github.com/aosp-mirror/platform_bionic/blob/master/android-changes-for-ndk-developers.md#correct-sonamepath-handling-available-in-api-level--23>`_).
* Fix `ctypes.pythonapi` and :any:`sys.abiflags`, and provide partial implementation of
  :any:`sysconfig.get_config_vars`.
* Fix native crash in `lrintf` / `feholdexcept` / `fegetenv` (Crystax issue `#1369
  <https://tracker.crystax.net/issues/1369>`_).
* Fix :any:`pkgutil.get_data` when used with `extractPackages`, and improve `extractPackages`
  performance.

3.3.0 (2018-06-20)
==================

* Add fast conversions between Python `bytes`/`bytearray` and Java `byte[]` (`#41
  <https://github.com/chaquo/chaquopy/issues/41>`_).
* Make pip evaluate environment markers (:pep:`508`) and `data-requires-python` attributes
  (:pep:`503`) against the target platform rather than the build platform.
* Make pip only prioritize native wheels (not pure-Python wheels) over sdists of a newer
  version.
* Fix pip issues when multiple packages provide the same directory or filename.
* Improve pip error messages when packages attempt to build native code.

..
   3.2.1 was a non-public release to enable the integration test
   ChaquopyPlugin.test_upgrade_3_2_1.

3.2.0 (2018-06-06)
==================

* Add `Python.getPlatform <java/com/chaquo/python/Python.html#getPlatform()>`_ and
  `AndroidPlatform.getApplication
  <java/com/chaquo/python/android/AndroidPlatform.html#getApplication()>`_.
* Make sure `__spec__` is set on modules which are loaded by direct calls to the loader, or via
  :any:`imp`.
* Fix :any:`hashlib` OpenSSL integration.
* Fix pip `--no-binary` option.
* Improve up-to-date checks on Gradle tasks.

3.1.0 (2018-05-30)
==================

* Add support for installing pure-Python sdists. This means that all pure-Python packages on
  PyPI should now work with Chaquopy, whether they have wheels available or not. If you have
  any difficulty installing a package, please report it at our `issue tracker
  <https://github.com/chaquo/chaquopy/issues>`_.

  * Because of this change, the Python major version of :ref:`buildPython <buildPython>` is now
    required to be the same as that of the app itself when using pip, and the default value of
    `buildPython` has been changed accordingly.

* Fix :any:`imp.find_module` and :any:`imp.load_module`.
* Implement implicit namespace packages on Python 3 (:pep:`420`).
* Add partial support for :any:`.pth files <site>`. Only the execution of lines starting with
  `import` is currently implemented: all other lines are ignored.
* Add message explaining how to show full pip output in Android Studio 3.1's new Build window.
* Fix "registering invalid inputs" warning in Android Studio 3.1.

3.0.0 (2018-05-15)
==================
* Android Gradle plugin version 3.1 is now supported.
* [**BACKWARD INCOMPATIBLE**] Android Gradle plugin version 2.2 is no longer supported. If
  you're still using Android Studio 2.2, then we highly recommend that you upgrade to the
  current version 3.1. Our testing shows that it builds apps more than twice as fast, whether
  you're using Chaquopy or not.
* Add Python versions 2.7.15 and 3.6.5, and fix a few lesser-used standard library modules.
* Update to pip version 10.0.1.
* Build reliability fixes, including one for `over-strict metadata parsing
  <https://github.com/dateutil/dateutil/issues/720>`_.
* Further build speed improvements.
* Improve app startup speed where a requirement is reinstalled at the same version as before.

2.1.0 (2018-04-26)
==================

* Add ability to load native library dependencies. This is required by the newly-added packages
  for PyZMQ and SciPy.
* Improve pip install performance.

2.0.1 (2018-03-22)
==================

* Fix a crash reported on various devices, especially Samsung Galaxy J series phones.
* Fix NumPy dependency on libc functions not present in API level 17 and earlier.
* Remove debugging information from native modules. All native packages benefit from this, but
  especially NumPy, which is now smaller by 4 MB per ABI.
* Disable upgrade notification from bundled copy of pip.

2.0.0 (2018-03-15)
==================

* General performance improvements: the Python unit tests now run about 25% faster.
* [**BACKWARD INCOMPATIBLE**] The import hook now only looks up names in Java if they failed to
  import from Python. This significantly speeds up import of large Python packages. However, it
  means that importing a name which exists in both languages is no longer reported as an error:
  instead, the value from Python will be returned.
* Fix a crash on API level 15 caused by the license notification.

1.4.0 (2018-03-05)
==================

* The Python standard library is now loaded from compiled .pyc files by default (see
  :ref:`documentation <android-bytecode>`). As a result, startup of a minimal app is now 20-30%
  faster with Python 2, and 50-60% faster with Python 3. (Python 3 startup is still slower than
  Python 2, but only by 15-20%.)
* `sys.stdin` now returns EOF rather than blocking. If you want to run some code which takes
  interactive text input, you may find the `console app template
  <https://github.com/chaquo/chaquopy-console>`_ useful.
* The `write` method of `sys.stdout` and `sys.stderr` now returns the character count.
* Very long lines written to `sys.stdout` and `sys.stderr` are now split into slightly smaller
  fragments, to allow for the shorter Logcat message length limit in recent versions of Android.
* Fix a multi-threading deadlock.
* Apps built with an unlicensed copy of the SDK are now limited to a run-time of 5 minutes.

1.3.1 (2018-01-26)
==================

* Static proxy generator now handles non-ASCII source files correctly (`#27
  <https://github.com/chaquo/chaquopy/issues/27>`_).

1.3.0 (2018-01-15)
==================

* The following things now return reasonable values: `sys.argv`, `sys.executable`, and
  `platform.platform()`.
* The following modules now work correctly: `sqlite3`, `ssl` (`#23
  <https://github.com/chaquo/chaquopy/issues/23>`_), and `tempfile`. (Requires Python version
  to be 2.7.14 or 3.6.3.)
* `sys.stdout` and `sys.stderr` are now directed to the Android Logcat.
* Add `extractPackages`, and use it by default for `certifi
  <https://pypi.python.org/pypi/certifi>`_.

1.2.0 (2018-01-07)
==================

* Python source directory locations can now be configured in the `sourceSets` block, just like
  Java.
* `getClass`, when called on a Java object, now returns the Java object class rather than the
  proxy object class.
* Generated `static_proxy` Java files no longer produce build warnings.
* Ensure pip is re-run if local requirements or wheel file changes.
* Add Python 2.7.14.
* Include `distutils` and `doctest` modules (`#20
  <https://github.com/chaquo/chaquopy/issues/20>`_). (Requires Python version to be 2.7.14 or
  3.6.3.)

1.1.0 (2017-12-22)
==================

* Add Python 3.6 runtime (`#1 <https://github.com/chaquo/chaquopy/issues/1>`_).
* `buildPython` can now be Python 2.7 or 3.3+ (`#2
  <https://github.com/chaquo/chaquopy/issues/2>`_).
* Support configuration in product flavors (`#6
  <https://github.com/chaquo/chaquopy/issues/6>`_).
* Improve startup performance.

0.6.1 (2017-12-11)
==================

* Apps can now use certain native packages, including NumPy (`#14
  <https://github.com/chaquo/chaquopy/issues/14>`_), as well as some pure-Python packages which
  aren't available from PyPI in wheel format. To support this, the `build.gradle` syntax for calling
  `pip install` has been changed: please see :ref:`the documentation <android-requirements>`.
* Zero-initialized Java arrays can now be created in Python, by passing an integer to the array
  constructor rather than a sequence.

0.5.0 (2017-11-04)
==================
* Support Android Gradle plugin versions 2.2 (`#9
  <https://github.com/chaquo/chaquopy/issues/9>`_) and 3.0 (`#3
  <https://github.com/chaquo/chaquopy/issues/3>`_).
* Increase minimum API level to 15. This still covers `99% of active devices
  <https://developer.android.com/about/dashboards/index.html>`_.
* Fix array store type-checking on old Android versions.
* Add `java.detach`, and fix several multi-threading issues.

0.4.5 (2017-10-26)
==================

* Remove dependency on `six` (`#13 <https://github.com/chaquo/chaquopy/issues/13>`_).

0.4.4 (2017-10-24)
==================

* Fix implicit relative imports (`#12 <https://github.com/chaquo/chaquopy/issues/12>`_).

0.4.3 (2017-09-21)
==================

* Improve startup performance.

0.4.0 (2017-09-11)
==================

* Add dynamic_proxy and static_proxy.

0.3.0 (2017-07-28)
==================

* Reflect Java class hierarchy in Python.
* Represent Java exceptions with their actual classes.
* Support Python unbound method syntax when calling Java methods, i.e.
  `ClassName.method(instance, args)`.
* Release GIL when calling Java constructors.

0.2.0 (2017-07-04)
==================

* Add import hook.
* Allow nested classes to be accessed as attributes.
* Improve performance.

0.1.0 (2017-06-24)
==================

* First public release.
