Cross-language issues
#####################


Multi-threading
===============

Because Chaquopy is based on the CPython (the Python reference implementation), it is limited by
CPython's global interpreter lock (GIL). This means that although Python code may be run on any
number of threads, only one of those threads will be executing at any given moment.

The GIL is automatically released by a thread whenever Python code calls a Java method,
allowing Python code to run on other threads until the method returns.


Memory management
=================

It's possible to create a cross-language reference cycle if a Python object references a Java
object which, directly or indirectly, references the original Python object. Such a cycle
cannot be detected by the garbage collector in either language. To avoid a memory leak. either
use a weak reference somewhere in the cycle, or break the cycle manually once it's no longer
required.
