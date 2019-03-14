This file gives instructions for debugging a Chaquopy-based app with PyCharm Professional
2018.3, but it should be possible to adapt it to any other IDE which supports the PyDev remote
debugging protocol.


# Port forward

Select a free TCP port to use on your workstation: this will be referred to as the "IDE port".

If connecting over USB, run `adb reverse tcp:<target_port> tcp:<IDE_port>`, where
`target_port` is a free port on the target device.


# App setup

The `src` directory alongside this README contains a modified copy of the
[pydevd](https://github.com/fabioz/PyDev.Debugger) library. This replaces the pycharm-debug.egg
mentioned in the PyCharm documentation. Add it to your app, either:
* By copying its content into `src/main/python`, or
* By using the `sourceSets` block in `build.gradle`.

Add the following lines to your app to make it connect to the IDE.

    import pydevd
    pydevd.settrace('<hostname>', port=<port>)

If connecting over USB, the hostname should be `localhost`, and the port should be
`target_port` from the adb command above.

If connecting over a network, the hostname should be your workstation's address, and the port
should be the IDE port selected above.

If you don't want execution to suspend at this point, add the argument `suspend=False`. For
other available arguments, see `src/pydevd.py`.


# PyCharm

Click the Run/Debug Configurations list in the toolbar, then choose Edit Configurations.

Click the + button and add a new Python Remote Debug configuration.

Set the port to match the IDE port selected above.

Click the folder icon in "Path mappings", and add the following two entries:

    Local:  /path/to/app/src/main/python
    Remote: /android_asset/chaquopy/app.zip

    Local:  /path/to/app/build/generated/python/requirements/debug/common
            (replace "debug" if using a different variant)
    Remote: /android_asset/chaquopy/requirements-common.zip

If you're loading Python code from other locations on the target device, also add those
locations along with their corresponding local paths.

Changes to these mappings will not take effect on an active debugger session. If you need to
change them, stop the debugger first.

For convenience, you may also want to add the local directories to your PyCharm project (File >
Settings > Project > Project Structure > Add Content Root).

In the toolbar, make sure the new configuration is selected, then click the Debug button.

Start your app. The debugger should activate as soon as the app executes the `settrace` line.
