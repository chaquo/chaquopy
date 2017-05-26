java
####
The `java` module provides facilities to use Java classes and objects.

jclass
======
.. autofunction:: java.jclass

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

* A Java array obtained from a method or field is represented as a :any:`jarray` proxy object.
  Java array parameters and fields can also be assigned from any Python iterable.

* A Java object obtained from a method or field is initially represented as a :any:`jclass`
  proxy object for its actual run-time type, which is not necessarily the declared type of the
  method or field. It can be transformed into another compatible type using the :any:`cast`
  function.

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

JavaException
=============
.. autoclass:: java.JavaException
