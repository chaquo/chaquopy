Java API
########

The Java API provides facilities to use Python classes and objects from Java code. For examples
of how to use it, see the `demo app <https://github.com/chaquo/chaquopy>`_.

Quick start
===========

#. If necessary, call `Python.start()
   <java/com/chaquo/python/Python.html#start-com.chaquo.python.Python.Platform->`_.

#. Call `Python.getInstance() <java/com/chaquo/python/Python.html#getInstance-->`_ to get the
   interface to Python.

#. Call `getModule() <java/com/chaquo/python/Python.html#getModule-java.lang.String->`_ or
   `getBuiltins() <java/com/chaquo/python/Python.html#getBuiltins-->`_ to get a
   PyObject representing a Python module.

#. Use the `PyObject <java/com/chaquo/python/PyObject.html>`_ methods to access the module's
   functions, classes and other objects.

Reference
=========

For full documentation, see the `Javadoc <java/overview-summary.html>`_.
