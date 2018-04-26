Change log
##########

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

* [**BACKWARD INCOMPATIBLE**] The import hook now only looks up names in Java if they failed to
  import from Python. This significantly speeds up import of large Python packages. However, it
  means that importing a name which exists in both languages is no longer reported as an error:
  instead, the value from Python will be returned.
* General performance improvements: the Python unit tests now run about 25% faster.
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
  <https://github.com/chaquo/chaquopy/issues/23>`_), and `tempfile`. (Requires `python.version`
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
  <https://github.com/chaquo/chaquopy/issues/20>`_). (Requires `python.version` to be 2.7.14 or
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
  <https://github.com/chaquo/chaquopy/issues/14>`_), as well as pure-Python packages which aren't
  available from PyPI in wheel format. To support this, the `build.gradle` syntax for calling `pip
  install` has been changed: please see :ref:`the documentation <android-requirements>`.
* Zero-initialized Java arrays can now be created in Python, by passing an integer to the array
  constructor rather than a sequence.

0.5.0 (2017-11-04)
==================
* Support Android Gradle plugin versions 2.2 (`#9
  <https://github.com/chaquo/chaquopy/issues/9>`_) and 3.0 (`#3
  <https://github.com/chaquo/chaquopy/issues/3>`_).
* Increase minimum API level to 15. This is the default for new apps in Android Studio 3.0, and
  covers `99% of active devices <https://developer.android.com/about/dashboards/index.html>`_.
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
