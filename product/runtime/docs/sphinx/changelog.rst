Change log
##########

0.5.0 (2017-11-04)
==================
* Support Android Gradle plugin versions 2.2 (https://github.com/chaquo/chaquopy/issues/9) and 3.0 (https://github.com/chaquo/chaquopy/issues/3).
* Increase minimum API level to 15. This is the default for new apps in Android Studio 3.0, and covers 99% of active devices (https://developer.android.com/about/dashboards/index.html).
* Fix array store type-checking on old Android versions.
* Add `java.detach`, and fix several multi-threading issues.

0.4.5 (2017-10-26)
==================

* Remove dependency on `six` (https://github.com/chaquo/chaquopy/issues/13).

0.4.4 (2017-10-24)
==================

* Fix implicit relative imports (https://github.com/chaquo/chaquopy/issues/12).

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
