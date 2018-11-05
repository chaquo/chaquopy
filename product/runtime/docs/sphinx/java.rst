Java API
########

The Java API provides facilities to use Python classes and objects from Java code. For examples
of how to use it, see the `demo app <https://github.com/chaquo/chaquopy>`_.


Summary
=======

#. If necessary, call `Python.start()
   <java/com/chaquo/python/Python.html#start-com.chaquo.python.Python.Platform->`_.

#. Call `Python.getInstance() <java/com/chaquo/python/Python.html#getInstance-->`_ to get the
   interface to Python.

#. Call `getModule() <java/com/chaquo/python/Python.html#getModule-java.lang.String->`_ or
   `getBuiltins() <java/com/chaquo/python/Python.html#getBuiltins-->`_ to get a `PyObject
   <java/com/chaquo/python/PyObject.html>`_ representing a Python module.

#. Use the `PyObject <java/com/chaquo/python/PyObject.html>`_ methods to access the module's
   functions, classes and other objects.


Examples
========

The following all assume `py` is a `Python <java/com/chaquo/python/Python.html>`_ instance.

Modules, classes, attributes and methods::

    # Python code                             // Java equivalent
    import zipfile                            PyObject zipfile = py.getModule("zipfile")
    zf = zipfile.ZipFile(                     PyObject zf = zipfile.callAttr("ZipFile",
      "example.zip")                                                         "example.zip");
    zf.debug = 2                              zf.put("debug", 2);
    zf.comment                                zf.get("comment");
    zf.write(                                 zf.callAttr("write",
      "filename.txt",                                     "filename.txt",
      compress_type=zipfile.ZIP_STORED)                   new Kwarg("compress_type",
                                                                    zipfile.get("ZIP_STORED")));

Built-in types and functions::

    # Python code                             // Java equivalent
                                              PyObject builtins = py.getBuiltins();
    l = [2, 1, 3]                             PyObject l = builtins.callAttr("list", 2, 1, 3);
    sorted(l)                                 builtins.callAttr("sorted", l);
    l[0]                                      l.callAttr("__getitem__", 0);
    l[0] = 42                                 l.callAttr("__setitem__", 0, 42);

    d = {1: "a", 2: "b"}                      PyObject d = builtins.callAttr("dict");
                                              d.callAttr("__setitem__", 1, "a");
                                              d.callAttr("__setitem__", 2, "b");

Type conversion::

    # Python code                             // Java equivalent
    import sys                                PyObject sys = py.getModule("sys");
    ms = sys.maxsize                          int ms = sys.get("maxsize").toJava(int.class);
    version = sys.version                     String version = sys.get("version").toString()


Reference
=========

For full documentation, see the `Javadoc <java/overview-summary.html>`_.
