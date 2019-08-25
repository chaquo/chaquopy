# Change log

This file only records changes to the demo app. For changes to the Chaquopy SDK itself, see
[its own change log](https://chaquo.com/chaquopy/doc/current/changelog.html).

## 6.3.0 (2019-08-25)

* Target Android Studio 3.5.0.
* Prevent crash by limiting the console scrollback size.

## 6.2.1 (2019-04-19)

* No changes except for the SDK update.

## 6.0.0 (2019-03-09)

* Target Android Studio 3.3.2.
* Add ABI `x86_64`.

## 5.1.2 (2019-01-19)

* Target Android Studio 3.2.1.
* Increase target API level to 28.

## 5.0.0 (2018-11-05)

* Remove Python 2 flavor.
* Add ABI `arm64-v8a`.
* Increase minSdkVersion to 16.

## 4.0.0 (2018-08-22)

* Target Android Studio 3.1.4.
* Correct caption mistake.

## 3.3.2 (2018-08-01)

* No changes except for the SDK update.

## 3.3.0 (2018-06-20)

* Target Android Studio 3.1.3.

## 3.2.0 (2018-06-06)

* Create PythonConsoleActivity background thread from Python rather than Java

## 3.1.0 (2018-05-30)

* Make Python 3 the default flavor.
* Don't suppress keyboard predictions in ConsoleActivity base class.

## 3.0.0 (2018-05-15)

* Target Android Studio 3.1, and update to Python 2.7.15 and 3.6.5.

## 2.1.0 (2018-04-26)

* No changes except for the SDK update.

## 2.0.1 (2018-03-22)

* No changes except for the SDK update.

## 2.0.0 (2018-03-15)

* Remove READ_LOGS permission: this was only needed on API level 15, and its Google Play
  description is too scary.

## 1.4.0 (2018-03-05)

* Increase target API level to 26.
* Console activities are now based on the [console app
  template](https://github.com/chaquo/chaquopy-console), giving the following improvements:
  * Code input in the REPL is now executed on a background thread.
  * The REPL can now be terminated by typing `exit()`, then restarted by pressing back and
    re-entering the activity.
  * Stderr is now shown in red.
  * Scrolling, rotation and state restoration are all more reliable.

## 1.3.1 (2018-01-26)

* Python console now handles non-ASCII text correctly.

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

* Fix garbage collection tests on API levels 17-19
  ([#17](https://github.com/chaquo/chaquopy/issues/17)).
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
