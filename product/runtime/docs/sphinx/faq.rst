FAQ
###

General
=======

.. _faq-name:

What does Chaquopy's name mean?
-------------------------------

It comes from Jack London’s use of the word "chechaquo" (now usually spelled `"cheechako"
<https://en.wiktionary.org/wiki/cheechako>`_), a Native American term meaning “newcomer”. We
chose it to reflect our goal of opening up new frontiers in how Python can be used.

.. _faq-react:

Does Chaquopy support React Native?
-----------------------------------

Yes, it can be used with any framework which lets you do the following:

* Add content to your app's build.gradle files.
* Call Java methods.

.. _faq-ios:

Does Chaquopy support iOS?
--------------------------

Not at the moment. For a list of ways to use Python in iOS apps, see the `Python wiki
<https://wiki.python.org/moin/Android>`_ ("iOS" column on the right).

One good option is the `BeeWare <https://beeware.org/>`_ framework. For example, have a look at
the Electron Cash iOS app (`source code
<https://github.com/Electron-Cash/Electron-Cash/tree/master/ios>`__, `App Store
<https://apps.apple.com/us/app/electron-cash/id1359700089>`__), which you can compare with the
similar Chaquopy-based Android app (`source code
<https://github.com/Electron-Cash/Electron-Cash/tree/master/android>`__, `Google Play
<https://play.google.com/store/apps/details?id=org.electroncash.wallet>`__).


.. _faq-size:

How can I make my app smaller?
------------------------------

If your app is too large, check the following:

* Your :ref:`Python source code <android-source>` directories: all files in there will be built
  into the app.
* Your :ref:`pip requirements list <android-requirements>`.

You can also try reducing the :ref:`number of ABIs <android-abis>` in your APK. Because of
the way Chaquopy packages its native components, the `APK splits
<https://developer.android.com/studio/build/configure-apk-splits.html>`_ and `app bundle
<https://developer.android.com/guide/app-bundle/>`_ features won't help much. Instead, use a
`product flavor dimension
<https://developer.android.com/studio/build/build-variants.html#product-flavors>`_ to build
separate APKs or app bundles for each ABI. If you plan to release your app on Google Play, each
flavor must also have a `different version code
<https://developer.android.com/google/play/publishing/multiple-apks#VersionCodes>`_. For
example:

.. tabs::

    .. code-tab:: kotlin

        android {
            val versionBase = 123
            flavorDimensions += "abi"
            productFlavors {
                create("arm32") {
                    dimension = "abi"
                    ndk { abiFilters += listOf("armeabi-v7a") }
                    versionCode = 1000000 + versionBase
                }
                create("arm64") {
                    dimension = "abi"
                    ndk { abiFilters += listOf("arm64-v8a") }
                    versionCode = 2000000 + versionBase
                }
            }
        }

    .. code-tab:: groovy

        android {
            def versionBase = 123
            flavorDimensions "abi"
            productFlavors {
                create("arm32") {
                    dimension = "abi"
                    ndk { abiFilters "armeabi-v7a" }
                    versionCode = 1000000 + versionBase
                }
                create("arm64") {
                    dimension = "abi"
                    ndk { abiFilters "arm64-v8a" }
                    versionCode = 2000000 + versionBase
                }
            }
        }

If your app uses TensorFlow, consider replacing it with `TensorFlow Lite
<https://www.tensorflow.org/lite/guide>`_:

* Install it by adding `tflite-runtime` to the :ref:`pip block <android-requirements>` of your
  build.gradle file.
* `Convert your model <https://www.tensorflow.org/lite/convert/>`_ to tflite format.
* `Run your model
  <https://www.tensorflow.org/lite/guide/python#run_an_inference_using_tflite_runtime>`_ using
  the tflite API.


.. _faq-obfuscate:

How can I obfuscate my code?
----------------------------

As described :ref:`here <android-bytecode>`, your code is automatically compiled to .pyc
format if possible. To make the build fail if a compatible Python version isn't found,
you can use the `src = true` setting.

If you want to hide your code further, you can compile it into an .so file using Cython
and our package build tool. For more details, see `here
<https://github.com/chaquo/chaquopy/issues/800#issuecomment-1413451177>`_.


.. _faq-mirror:

The Maven or pip repository is unreliable from my location
----------------------------------------------------------

To make your own mirror of our Maven repository:

* Download the following directories from `Maven Central
  <https://repo.maven.apache.org/maven2/com/chaquo/python/>`_, and arrange them in the same
  structure as the server. To find which Python version goes with which Chaquopy version, see
  :doc:`this table <../versions>`.

  * `com/chaquo/python/com.chaquo.python.gradle.plugin/CHAQUOPY_VERSION`
  * `com/chaquo/python/gradle/CHAQUOPY_VERSION`
  * `com/chaquo/python/runtime/*/CHAQUOPY_VERSION`
  * `com/chaquo/python/target/PYTHON_VERSION`
* Edit the `repositories` block in your `settings.gradle` or `build.gradle` file to `declare
  your repository
  <https://docs.gradle.org/current/userguide/declaring_repositories.html#sec:declaring_multiple_repositories>`_
  before or instead of `mavenCentral`. Use the directory containing "com": either an HTTP URL
  or a local path can be used.

To make your own mirror of our pip repository:

* Download whatever packages your app needs from https://chaquo.com/pypi-13.1/, and
  arrange them in the same directory structure as the server.
* Add the following lines to the :ref:`pip block <android-requirements>` of your build.gradle
  file:

  .. code-block:: kotlin

      options("--index-url", "https://pypi.org/simple/")
      options("--extra-index-url", "YOUR_MIRROR")

  Where `YOUR_MIRROR` is the directory containing the package directories you downloaded
  above. Either an HTTP URL or a local path can be used.


How do I ...
============

.. _faq-read:

Read files in Python
--------------------

To read a file from your source code directory, use a path relative to `__file__`, as described
in the ":ref:`android-data`" section.

To upload files to the device while your app is running, use `os.environ["HOME"]` and the
Device File Explorer, as described in the ":ref:`android-os`" section.

To read photos, downloads, and other files from the external storage directory ("sdcard"), see
:ref:`the question below <faq-sdcard>`.

.. _faq-sdcard:

Read files from external storage ("sdcard")
-------------------------------------------

Since API level 29, Android has a `scoped storage policy
<https://developer.android.com/training/data-storage#scoped-storage>`_ which prevents direct
access to external storage, even if your app has the `READ_EXTERNAL_STORAGE` permission.
Instead, you can use the `system file picker
<https://developer.android.com/training/data-storage/use-cases#open-document>`_, and pass the
file to Python as a byte array:

.. code-block:: kotlin

    val REQUEST_OPEN = 0

    fun myMethod() {
        startActivityForResult(
            Intent(if (Build.VERSION.SDK_INT >= 19) Intent.ACTION_OPEN_DOCUMENT
                   else Intent.ACTION_GET_CONTENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                setType("*/*")
            }, REQUEST_OPEN)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == REQUEST_OPEN && resultCode == RESULT_OK) {
            val uri = data!!.data!!
            // For Java, see https://stackoverflow.com/a/10297073
            val content = contentResolver.openInputStream(uri)!!.use { it.readBytes() }
            myPythonModule.callAttr("process", content)
        }
    }

The Python function can then access the file content however you like:

.. code-block:: python

    def process(content):
        # `content` is already a bytes-like object, but if you need a standard bytes object:
        content = bytes(content)

        # If you need a file-like object:
        import io
        content_file = io.BytesIO(content)

        # If you need a filename (less efficient):
        import tempfile
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(content)
            filename = temp_file.name  # Valid only inside the `with` block.

.. _faq-write:

Write files in Python
---------------------

Use `os.environ["HOME"]`, as described in the ":ref:`android-os`" section.

.. _faq-images:

Pass images to/from Python
--------------------------

The easiest way is to encode the image as a PNG or JPG file and pass it as a byte array. For an
example of this, see the `chaquopy-matplotlib <https://github.com/chaquo/chaquopy-matplotlib>`_
app.

You may get better performance by passing the raw image data as an :ref:`array
<python-array-convert>`, but then you'll be responsible for using the correct image dimensions
and pixel format.

.. _faq-callback:

Call back from Python
---------------------

There are many ways of doing this: here's one example from the Electron Cash project:

* Kotlin code `passes a method reference <https://github.com/Electron-Cash/Electron-Cash/blob/android-4.2.3-2/android/app/src/main/java/org/electroncash/electroncash3/Daemon.kt#L41>`_
  to Python.
* The Python code creates a background thread which later `calls the method <https://github.com/Electron-Cash/Electron-Cash/blob/android-4.2.3-2/android/app/src/main/python/electroncash_gui/android/console.py#L235>`_
  using normal Python syntax.


Build errors
============

First, make sure you're seeing the complete build log in Android Studio:

* In version 3.6 and newer, click the "Build: failed" caption to the left of the message.
* In version 3.5 and older, click the "Toggle view" button to the left of the message.

Chaquopy cannot compile native code
-----------------------------------

You're trying to install a native package which we haven't built yet. There may be a different
version available, in which case there will be a "pre-built wheels" message in the build log.
Otherwise, please visit our `issue tracker <https://github.com/chaquo/chaquopy/issues>`_ for
help.

No Python interpreter configured for the module
-----------------------------------------------

This message is harmless: see the ":ref:`android-studio-plugin`" section.

No version of NDK matched the requested version
-----------------------------------------------

This can be fixed by `installing the NDK version
<https://developer.android.com/studio/projects/install-ndk#specific-version>`__ mentioned in the
message, or upgrading to Android Gradle plugin version 4.1 or later.

The warning "Compatible side by side NDK version was not found" is harmless, but can be
resolved in the same ways.


Runtime errors
==============

Depending on your Android version, a crashing app may show a message that it "has stopped" or
"keeps stopping", or the app might just disappear. Either way, you can find the stack trace in
the `Logcat <https://stackoverflow.com/a/23353174>`_. Some of the most common exceptions are
listed below.

FileNotFoundError
-----------------

See the questions above about :ref:`reading <faq-read>` and :ref:`writing <faq-write>` files.

Read-only file system
---------------------

See the question above about :ref:`writing <faq-write>` files.

ModuleNotFoundError
-------------------

Make sure you've built all required packages into your app using the :ref:`pip block
<android-requirements>` in your build.gradle file.

No address associated with hostname
-----------------------------------

Make sure your app has the `INTERNET permission <https://stackoverflow.com/q/2378607>`_, and
the device has Internet access.
