/**
 * **Quick start guide:**
 *
 * 1. If necessary, call {@link com.chaquo.python.Python#start Python.start()}:
 *        * If running on Android, pass a `new {@link com.chaquo.python.AndroidPlatform#AndroidPlatform
 *          AndroidPlatform}(context)`, where `context` is an `Activity`, `Service` or `Application`
 *          object from your app.
 *        * If running on a standard Java VM, and you want to customize the Python startup process,
 *          pass a {@link com.chaquo.python.GenericPlatform}.
 *        * Otherwise, you don't need to call `Python.start()`, and can proceed directly to the next step.
 * 1. Call {@link com.chaquo.python.Python#getInstance()} to get the interface to Python.
 * 1. Call {@link com.chaquo.python.Python#getModule getModule()} or
 *    {@link com.chaquo.python.Python#getBuiltins getBuiltins()} to get a
 *    {@link com.chaquo.python.PyObject} for a Python module.
 * 1. Use the {@link com.chaquo.python.PyObject} methods to access the module's functions, classes
 *    and other objects. */
package com.chaquo.python;
