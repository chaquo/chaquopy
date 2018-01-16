# Change log

This file only records changes to the demo app. For changes to Chaquopy itself, see
https://chaquo.com/chaquopy/doc/current/changelog.html.

## 1.3.0 (2018-01-15)

* Stop logging stdout and stderr: Chaquopy now does this automatically.

## 1.2.0 (2018-01-07)

* Provide separate icons for Python 2 and Python 3.
* Upgrade Python 2 version to 2.7.14.
* Fix font in API level 21.
* Make ConsoleActivity easier to reuse ([chaquopy-hello
  #2](https://github.com/chaquo/chaquopy-hello/issues/2)).
* Don't paste formatting into Python console input box.
* Unit test cleanups and performance improvements.

## 1.1.0 (2017-12-22)

* Now available for Python 3 (search "Chaquopy Python 3" on Google Play).

## 0.6.1 (2017-12-11)

* Fix garbage collection tests on API levels 17-19 ([#17](https://github.com/chaquo/chaquopy/issues/17)).
* Fix most flake8 warnings.
* Rearrange Python package structure.

## 0.5.0 (2017-11-04)

* Target Android Studio 3.0 ([#3](https://github.com/chaquo/chaquopy/issues/3)).
* Make GIL tests more reliable ([#7](https://github.com/chaquo/chaquopy/issues/7)).

## 0.4.5 (2017-10-26)

* Remove dependency on `six` ([#13](https://github.com/chaquo/chaquopy/issues/13)).

## 0.4.3 (2017-09-21)

* Fix stdout and stderr handling when switching between ConsoleActivity subclasses.

## 0.4.1 (2017-09-15)

* Fix crash when notification sounds are disabled.
* Save UI demo activity state across screen rotation.

## 0.4.0 (2017-09-11)

* Add Android UI demo and Java API demo.

## 0.3.0 (2017-07-28)

* Fix issues when re-entering the app from the recent apps button.

## 0.2.1 (2017-07-04)

* Fix line wrapping.
* Remove unused languages from support library.

## 0.2.0 (2017-07-04)

* Allow multi-line input in REPL.
* Retain REPL state when back button pressed.
* Highlight REPL input in bold.

## 0.1.0 (2017-06-24)

* First public release.
