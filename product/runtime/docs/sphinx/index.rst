java
####
The `java` module provides facilities to use Java classes and objects.

Data types
==========

Overview
--------
Python and Java data types are converted as follows:

* Java `null` corresponds to Python `None`.

* The Java boolean, integer and floating point types correspond to Python `bool`, `int` and
  `float` respectively. (The Python 2 types `int` and `long` are treated as equivalent.)
  Auto-boxing and unboxing is also implemented.

* Java `String` and `char` both correspond to a Python Unicode string. (In Python 2, a byte
  string is also accepted.)

* A Java object is represented as a :any:`jclass` proxy object.

* A Java array is represented as a :any:`jarray` proxy object. Java array parameters and fields
  can also be implicitly converted from any Python iterable, except a string.

.. note:: A Java object or array obtained from a method or field will intially be represented
          as a proxy for its actual run-time type, which is not necessarily the declared type
          of the method or field. It can be viewed as another compatible type using the
          :any:`cast` function.

jclass
------
.. autofunction:: java.jclass

Primitive wrappers
------------------
.. autoclass:: java.jboolean
.. autoclass:: java.jbyte
.. autoclass:: java.jshort
.. autoclass:: java.jint
.. autoclass:: java.jlong
.. autoclass:: java.jfloat
.. autoclass:: java.jdouble
.. autoclass:: java.jchar

jarray
------
.. autofunction:: java.jarray

cast
----
.. autofunction:: java.cast(cls, obj)

Exceptions
==========
.. autoclass:: java.JavaException
