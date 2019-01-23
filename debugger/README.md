This file gives instructions for debugging a Chaquopy-based app with PyCharm Professional
2018.3, but it should be possible to adapt it to any other IDE which supports the PyDev remote
debugging protocol.


# Port forward

Run `adb reverse tcp:5678 tcp:5678`. The first number identifies the target device port, the
second number the IDE port. You can change either or both of them if you want.


# App setup

The `src` directory alongside this README contains a modified copy of the
[pydevd](https://github.com/fabioz/PyDev.Debugger) library. This replaces the pycharm-debug.egg
mentioned in the PyCharm documentation. Add it to your app, either:
* By copying its content into `src/main/python`, or
* By using the `sourceSets` block in `build.gradle`.

Add the following lines to your app to make it connect to the IDE. The `port` should match the
"target device port" from the adb command above.

    import pydevd
    pydevd.settrace('localhost', port=5678)

If you don't want execution to suspend at this point, add the argument `suspend=False`. For
other available arguments, see `src/pydevd.py`.


# PyCharm

Click the Run/Debug Configurations list in the toolbar, then choose Edit Configurations.

Click the + button and add a new Python Remote Debug configuration.

Set the port to match the "IDE port" from the adb command above.

Click the folder icon in "Path mappings", and add the following two entries:

    Local:  /path/to/app/src/main/python
    Remote: /android_asset/chaquopy/app.zip

    Local:  /path/to/app/build/generated/python/requirements/debug/common
            (replace "debug" if using a different variant)
    Remote: /android_asset/chaquopy/requirements-common.zip

Changes to these mappings will not take effect on an active debugger session. If you need to
change them, stop the debugger first.

For convenience, you may also want to add the local directories to your PyCharm project (File >
Settings > Project > Project Structure > Add Content Root).

In the toolbar, make sure the new configuration is selected, then click the Debug button.

Start your app. The debugger should activate as soon as the app executes the `settrace` line.
