# Performance test procedure

Use the pkgtest app as follows (process for older versions varied as noted in the
table):

* Chaquopy release build – temporarily edit the top-level build.gradle file to set the
  version.
* App debug build
* scipy and matplotlib
* abiFilters set to arm64-v8a and x86_64

Before each "First run", go to app info and clear storage. For "Second run", go to app
info and force stop, because swiping away in the Recents screen does not reliably kill
the process.

Times are in seconds, best of 3:
* "Startup" is the time from the logcat message "Displayed com.application.id: +123ms".
* "Test" is the time reported by the tests themselves.

Sizes are as reported in Settings:
* "App MB" includes not only the APK, but also native libraries if they're extracted
  from the APK, and probably AOT-compiled Java code.
* "Data MB" is difficult to pin down on the Pixel 7, maybe for reasons connected to the
  WebView mentioned below:
  * It's usually a few MB larger than the size of the /data/data subdirectory, except
    perhaps the first time you check it after clearing storage and re-running. But then
    leaving and re-entering the Storage page makes the extra size appear permanently, so
    this is included in the table.
  * Sometimes it increases by an *additional* 4 MB while the app is running, but this
    always goes away when you force stop, so it's *not* included in the table.

```
                             First run         Second run
                           Startup   Test    Startup   Test    App MB    Data MB
Samsung J2
   8.0.0                      3.46  13.81       3.20   7.73      76.7       59.2
   8.0.1                      3.57  13.80       3.38   7.79      76.9       59.2
   9.0.0                      3.56  14.25       3.34   7.70      77.3       59.2
   9.1.0                      3.49  14.29       3.30   7.59      78.5       59.3

Nexus 4
   9.1.0                      3.52  17.49       3.48   8.91      78.8       59.3
  10.0.1                      3.82  19.50       3.61   9.04      76.8       59.4

* Updated NumPy from 1.17.4 to 1.19.5.
* Changed Chaquopy build type from debug to release.

  10.0.1                      3.62  19.46       3.31  11.01      75.7       58.7
  11.0.0                      3.62  20.39       3.28  11.08      75.7       58.6
  12.0.0                      3.65  19.03       3.35  10.47      76.0       58.7
  12.0.1                      3.54  20.68       3.47  10.43      76.0       58.6
  13.0.0                      3.45  18.17       3.08  10.76      76.2       58.8

* I think the Data increase here was caused by a Chrome update on the device, which
  means we now have a 4 MB file app_webview/BrowserMetrics-spare.pma. Re-testing 13.0.0
  now shows a Data size of 62.7 MB, the same as 14.0.2.

  14.0.2                      3.40  18.97       3.06  11.31      76.1       62.7

* Changed abiFilters from armeabi-v7a and x86 to arm64-v8a and x86_64.
* Startup times now use the time from the "Displayed com.application.id: +123ms" message.
  Previously we measured from the first to the last message mentioning the application
  ID, which is roughly the same.

Pixel 7
  14.0.2                      0.64  1.51        0.62  0.89       78.7       67.7
  15.0.1                      0.61  1.54        0.55  0.93       78.7       68.0

* Re-testing 15.0.1 now shows an App size of 84.4 MB, and even the APK is bigger than 80,
  so most of the increase here is probably caused by new versions of the AGP or the
  app's Java dependencies.

  16.0.0                      0.63  1.50        0.60  0.91       84.9       68.3
```
