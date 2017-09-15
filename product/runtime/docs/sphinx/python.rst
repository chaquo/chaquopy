Python API
##########

The `java` module provides facilities to use Java classes and objects from Python code. For
examples of how to use it, see the `demo app <https://github.com/chaquo/chaquopy>`_.

Import hook
===========

The import hook allows you to write code like `from java.lang import String`, which is
equivalent to `String = jclass("java.lang.String")`.

* **Only the "from ... import ..." form is supported**, e.g. `import java.lang.String` will not
  work.
* Wildcard import is not supported, e.g. `from java.lang import *` will not work.
* Only classes and interfaces can be imported from Java, not packages, e.g. `import java.lang` and
  `from java import lang` will not work.
* Nested and inner classes cannot be imported directly. Instead, import the outer class,
  and access the nested class as an attribute, e.g. `Outer.Nested`.

To avoid confusion, it's recommended to avoid having a Java package and a Python module with
the same name. However, this is still possible, subject to the following points:

* Names imported from the Java package will not automatically be added as attributes of the
  Python module.

* Imports from both languages may be intermixed, even within a single `from ... import`
  statement. However, if you attempt to import a name which exists in both languages, an
  `ImportError` will be raised. This can be worked around by accessing the names indirectly.
  For example, if both Java and Python have a class named `com.example.Class`, then instead of
  `from com.example import Class`, you can access them like this::

    # By using "import" without "from", the Java import hook is bypassed.
    import com.example
    PythonClass = com.example.Class

    JavaClass = jclass("com.example.Class")

* Relative import syntax is supported. For example, within a Python module called
  `com.example.module`::

    from . import Class                # Same as "from com.example import Class"
    from ..other.package import Class  # Same as "from com.other.package import Class"

.. autofunction:: java.set_import_enabled(enable)

Data types
==========

Overview
--------

Data types are converted between Python and Java as follows:

* Java `null` corresponds to Python `None`.

* The Java boolean, integer and floating point types correspond to Python `bool`, `int` and
  `float` respectively. (The Python 2 types `int` and `long` are treated as equivalent.)
  Auto-boxing and unboxing is also implemented.

* Java `String` and `char` both correspond to a Python Unicode string. (In Python 2, a byte
  string is also accepted.)

* A Java object is represented as a :any:`jclass` object.

* A Java array is represented as a :any:`jarray` object. Java array parameters and fields
  can also be implicitly converted from any Python iterable, except a string.

.. note:: A Java object or array obtained from a method or field will be represented
          in Python as its actual run-time type, which is not necessarily the declared type
          of the method or field. It can be viewed as another compatible type using the
          :any:`cast` function.

.. _primitives:

Primitives
----------

A Python boolean, integer, float or string can normally be passed directly to a Java method or
field which takes a compatible type. Java has more primitive types than Python, so when more
than one compatible integer or floating-point overload is applicable for a method call, the
longest one will be used. Similarly, when a Python string is passed to a method which has
overloads for both `String` and `char`, the `String` overload will be used.

If these rules do not give the desired result, the following wrapper classes can be used to be
more specific about the intended type.

.. autoclass:: java.jboolean
.. autoclass:: java.jbyte
.. autoclass:: java.jshort
.. autoclass:: java.jint
.. autoclass:: java.jlong
.. autoclass:: java.jfloat
.. autoclass:: java.jdouble
.. autoclass:: java.jchar
.. autoclass:: java.jvoid

For example, if `p` is a `PrintStream
<https://docs.oracle.com/javase/8/docs/api/java/io/PrintStream.html>`_::

    p.print(42)              # will call print(long)
    p.print(jint(42))        # will call print(int)
    p.print(42.0)            # will call print(double)
    p.print(jfloat(42.0))    # will call print(float)
    p.print("x")             # will call print(String)
    p.print(jchar("x"))      # will call print(char)

The numeric type wrappers take an optional `truncate` parameter. If this is set, any excess
high-order bits of the given value will be discarded, as with a cast in Java. Otherwise,
passing an out-of-range value will result in an `OverflowError`.

.. note:: When these wrappers are used, Java overload resolution rules will be in effect
          for the wrapped parameter. For example, a `jint` will only be applicable to a
          Java `int` or larger, and the *shortest* applicable overload will be used.

Classes
-------

.. autofunction:: java.jclass(cls_name)

.. note:: Rather than calling this function directly, it's usually more convenient to use the
          `import hook`_.

Java classes and objects can be used with normal Python syntax::

    >>> Point = jclass("java.awt.Point")
    >>> p = Point(3, 4)
    >>> p.x
    3
    >>> p.y
    4
    >>> p.x = 7
    >>> p.getX()
    7.0

Overloaded methods are resolved according to Java rules::

    >>> from java.lang import String, StringBuffer
    >>> sb = StringBuffer(1024)
    >>> sb.append(True)
    >>> sb.append(123)
    >>> sb.append(cast(String, None))
    >>> sb.append(3.142)
    >>> sb.toString()
    u'true123null3.142'

If a method or field name clashes with a Python reserved word, it can be accessed by
appending an underscore, e.g. `print` becomes `print_`. The original name is still
accessible via :any:`getattr`.

Aside from attribute access, Java objects also support the following operations:

* `is` is equivalent to Java `==` (i.e. it tests object identity).
* `==` and `!=` call `equals
  <https://docs.oracle.com/javase/8/docs/api/java/lang/Object.html#equals(java.lang.Object)>`_.
* :any:`hash` calls `hashCode
  <https://docs.oracle.com/javase/8/docs/api/java/lang/Object.html#hashCode()>`_.
* :any:`str` calls `toString
  <https://docs.oracle.com/javase/8/docs/api/java/lang/Object.html#toString()>`_.
* The equivalent of the Java syntax `ClassName.class` is `ClassName.getClass()`; i.e. the
  `getClass()` method can be called on a class as well as an instance.

The Java class hierarchy is reflected in Python, e.g. if `s` is a Java `String` object, then
`isinstance(s, Object)` and `isinstance(s, CharSequence)` will both return `True`. All array
and interface types are also considered subclasses of `java.lang.Object`.

Arrays
------

Any Python iterable (except a string) can normally passed directly to a Java method or field
which takes an array type. But where a method has multiple equally-specific overloads, the
value must be converted to a Java array object to disambiguate the call.

For example, if a class defines the methods `f(long[] x)` and `f(int[] x)`, calling
`f([1,2,3])` will fail with an ambiguous overload error. To call the `int[]` overload, use
`f(jarray(jint)([1,2,3]))`.

.. autofunction:: java.jarray

A `jarray` class can be instantiated with any Python iterable to create an equivalent Java
array. For example::

    # Python code                           # Java equivalent
    jarray(jint)([1, 2, 3])                 # new int[]{1, 2, 3}
    jarray(jarray(jint))([[1, 2], [3, 4]])  # new int[][]{{1, 2}, {3, 4}}
    jarray(String)(["Hello", "world"])      # new String[]{"Hello", "world"}
    jarray(jchar)("hello")                  # new char[] {'h', 'e', 'l', 'l', 'o'}

Array objects support the following operations:

* The basic Python sequence protocol:
   * Reading and writing using `[]` syntax.
   * Searching using `in`.
   * Iteration using `for`.
   * Since Java arrays are fixed-length, they do not support `del` or any other way of adding or
     removing elements.
* `is` is equivalent to Java `==` (i.e. it tests object identity).
* `==` and `!=` can compare the contents of the array with any Python iterable (including
  another Java array).
* Like Python lists, Java array objects are not hashable in Python because they're mutable.
* `str` returns a representation of the array contents.
* All arrays are instances of `java.lang.Object`, so the methods `toString`, `equals` and
  `hashCode` may also be called, though their implementations for arrays are unlikely to be
  useful.

Casting
-------

.. autofunction:: java.cast(cls, obj)

Inheriting Java classes
=======================

To allow Python code to be called from Java without using the Chaquopy :doc:`Java API <java>`,
you can inherit from Java classes in Python. To make your inherited class visible to the Java
virtual machine, a corresponding Java proxy class must be generated, and there are two ways of
doing this:

* A `dynamic proxy`_ uses the `java.lang.reflect.Proxy
  <https://docs.oracle.com/javase/7/docs/api/java/lang/reflect/Proxy.html>`_ mechanism to
  generate a Java class at runtime.
* A `static proxy`_ uses a build-time tool to generate Java source code.

Dynamic proxy
-------------

.. note:: For further examples of how dynamic proxies can be used, see the corresponding `unit tests
          <https://github.com/chaquo/chaquopy/tree/master/app/src/main/python/test_proxy.py>`_.

.. autofunction:: java.dynamic_proxy(*implements)

Dynamic proxy classes are implemented just like regular Python classes, but any method names
which appear in the specified interfaces will be visible to Java. For example::

    >>> from java.lang import Runnable, Thread
    >>> class R(dynamic_proxy(Runnable)):
    ...     def __init__(self, name):
                super(R, self).__init__()
                self.name = name
    ...     def run(self):
    ...         print("Running " + self.name)
    ...
    >>> r = R("hello")
    >>> t = Thread(r)
    >>> t.getState()
    <java.lang.Thread$State 'NEW'>
    >>> t.start()
    Running hello
    >>> t.getState()
    <java.lang.Thread$State 'TERMINATED'>

If Java code calls an interface method which is not implemented by the Python class, a
`PyException <java/com/chaquo/python/PyException.html>`_ will be thrown.

Dynamic proxy classes have the following restrictions:

* They cannot extend Java classes, only implement Java interfaces.
* They cannot be referenced by name in Java source code.
* They cannot be instantiated in Java, only in Python.

If you need to do any of these things, you'll need to use a `static proxy`_ instead.

.. _static-proxy:

Static proxy
------------

.. note:: For futher examples of how static proxies can be used, see the `class declarations
          <https://github.com/chaquo/chaquopy/tree/master/app/src/main/python/static_proxy>`_
          in the unit tests, and the corresponding `Java code
          <https://github.com/chaquo/chaquopy/tree/master/app/src/main/java/com/chaquo/java/StaticProxyTest.java>`_
          which uses those classes.

.. autofunction:: java.static_proxy(extends=None, *implements, package=None, modifiers="public")

To add members to the generated Java class, use the following decorators:

.. autofunction:: java.constructor(arg_types, *, modifiers="public", throws=None)
.. autofunction:: java.method(return_type, arg_types, *, modifiers="public", throws=None)
.. autofunction:: java.Override(return_type, arg_types, *, modifiers="public", throws=None)

Notes on the decorators:

* Multiple decorators may be used on the same method, in which case multiple Java signatures
  will be generated for it (see notes on overloading below).
* Java types must be specified as one of the following:
   * A Java class imported using the `import hook`_.
   * A :any:`jarray` type.
   * One of the :ref:`primitive types <primitives>`.
* `return_type` must be a single Java type, or :any:`jvoid`.
* `arg_types` must be a (possibly empty) list or tuple of Java types.
* `modifiers` must be a string which is copied to the generated Java declaration. For example,
  to make a method synchronized, you can pass `modifiers="public synchronized"`.
* `throws` must be a list or tuple of `java.lang.Throwable` subclasses.

Because the :ref:`static proxy generator <static-proxy-generator>` works by static analysis of the
Python source code, there are some restrictions on the code's structure:

* Only code which appears unconditionally at the module top-level will be processed.
* Java classes must be imported using the `import hook`_, not dynamically with :any:`jclass`.
  Nested classses can be referenced by importing the top-level class and then using attribute
  notation, e.g. `Outer.Nested`.
* The names bound by the `import` statement must be used directly. For example, after `from
  java.lang import IllegalArgumentException as IAE`, you may use `IAE` in a `throws`
  declaration. However, if you assign `IAE` to another variable, you cannot use that variable in
  a `throws` declaration, as the static proxy generator will be unable to resolve it.
* Similarly, string parameters must be given as literals.
* `import` statements using relative import syntax or `import *` will be ignored, except for
  `from java import *`, which will import all names documented on this page.

Notes
-----

The following notes apply to both types of proxy:

* Classes may have any number of Python base classes, as long as the :any:`dynamic_proxy` or
  :any:`static_proxy` expression comes first.

* Classes may have any number of attributes, Those with the same names as inherited Java members
  will override or hide them as appropriate.

* Object instances may also have any number of attributes, but attempting to assign to an
  inherited Java member other than a non-final field will raise an `AttributeError`.

* Instances of proxy classes can be used just like Java instances. For example, they can be
  passed directly to any compatible Java method or field, and to :any:`cast`. `isinstance` will
  show that they are instances of the specified Java base classes, and of `java.lang.Object`.

* When Python methods are called from Python, the call always takes place directly. When Python
  methods are called from Java, the parameters and return value are converted as described in
  `data types`_ above. In particular, if the method is passed an array, including via varargs
  syntax ("..."), the Python method will receive it as a :any:`jarray` object.

* If a method is overloaded (i.e. it has multiple Java signatures), the Python signature should
  be able to accept them all. This can usually be achieved by some combination of `duck typing
  <https://en.wikipedia.org/wiki/Duck_typing>`_, default arguments, and `*args` syntax.

  However, this doesn't mean the Python method has to *implement* all the overloads. If there
  are any cases you don't want to override, you can call through to the base class
  implementation using one of the following forms:

   * `SuperClass.method(self, args)`
   * `super(ThisClass, self).method(args)`
   * `super().method(args)` (Python 3 only)

* Special methods:

   * If you override `__init__`, you must call through to the superclass `__init__` with zero
     arguments. Until this is done, the object cannot be used as a Java object. Supplying
     arguments to the superclass constructor is not currently possible.

   * If you override `__str__`, `__eq__` or `__hash__`, they will only be called when an object
     is accessed from Python. It's usually better to override the equivalent Java methods
     `toString`, `equals` and `hashCode`, which will take effect in both Python and Java. If
     any of these methods are not overridden, the default `java.lang.Object` implementation
     will be inherited.

   * If you override any other special method, make sure to call through to the superclass
     implementation for any cases you don't handle.


Exceptions
==========

Throwing
--------

`java.lang.Throwable` is represented as inheriting from the standard Python :any:`Exception`
class, so all Java exceptions can be thrown in Python.

When `inheriting Java classes`_, exceptions may propagate from Python to Java code:

* The Python and Java stack traces will be merged together in the exception, with Python frames
  having a class name of `<python>`.
* If the exception is of a Java type, the original exception object will be used. Otherwise, it
  will be represented as a `PyException <java/com/chaquo/python/PyException.html>`_.

Catching
--------

Exceptions thrown by Java methods will propagate into the calling Python code. The Java stack
trace is added to the exception message::

    >>> from java.lang import Integer
    >>> Integer.parseInt("abc")
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      ...
    java.lang.NumberFormatException: For input string: "abc"
            at java.lang.NumberFormatException.forInputString(NumberFormatException.java:65)
            at java.lang.Integer.parseInt(Integer.java:580)
            at java.lang.Integer.parseInt(Integer.java:615)

Java exceptions can be caught with standard Python syntax, including catching a subclass
exception via the base class:

    >>> from java.lang import IllegalArgumentException
    >>> try:
    ...     Integer.parseInt("abc")
    ... except IllegalArgumentException as e:
    ...     print type(e)
    ...     print e
    ...
    <class 'java.lang.NumberFormatException'>
    For input string: "abc"
            at java.lang.NumberFormatException.forInputString(NumberFormatException.java:65)
            at java.lang.Integer.parseInt(Integer.java:580)
            at java.lang.Integer.parseInt(Integer.java:615)
