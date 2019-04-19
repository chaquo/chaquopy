Java API
########

The Java API provides facilities to use Python classes and objects from Java code.


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

Primitive types::

    # Python code                             // Java equivalent
    import sys                                PyObject sys = py.getModule("sys");
    sys.maxsize                               sys.get("maxsize").toLong();
    sys.version                               sys.get("version").toString();
    sys.is_finalizing()                       sys.callAttr("is_finalizing").toBoolean();

Container types::

    # Python code                             // Java equivalent
    import sys                                PyObject sys = py.getModule("sys");
    sys.version_info[0]                       sys.get("version_info").asList().get(0).toInt();

    import os                                 PyObject os = py.getModule("os");
    os.environ["HELLO"]                       os.get("environ").asMap().get("HELLO").toString();
    os.environ["HELLO"] = "world"             os.get("environ").asMap().put(
                                                  PyObject.fromJava("HELLO"),
                                                  PyObject.fromJava("world"));

For more examples, see the `demo app <https://github.com/chaquo/chaquopy>`_.


Reference
=========

For full documentation, see the `Javadoc <java/overview-summary.html>`_.
