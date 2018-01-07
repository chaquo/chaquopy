Change log
##########

1.2.0 (2018-01-17)
==================

* Python source directory locations can now be configured in the `sourceSets` block, just like
  Java.
* `getClass`, when called on a Java object, now returns the Java object class rather than the
  proxy object class.
* Generated `static_proxy` Java files no longer produce build warnings.
* Ensure pip is re-run if local requirements or wheel file changes.
* Add Python 2.7.14.
* Include `distutils` and `doctest` modules (`#20
  <https://github.com/chaquo/chaquopy/issues/20>`_). For Python 2 apps, this also requires
  upgrading to Python 2.7.14.

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
  <https://github.com/chaquo/chaquopy/issues/14>`_), as well as pure-Python packages which
  aren't available from PyPI in wheel format. To support this, the `build.gradle` syntax for
  calling `pip install` has been changed: please see `the
  documentation <https://chaquo.com/chaquopy/doc/current/android.html#python-requirements>`_.
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
