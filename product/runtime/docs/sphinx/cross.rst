Cross-language issues
#####################


Multi-threading
===============

Chaquopy is thread-safe. However, because it's based on the CPython (the Python reference
implementation), it is limited by CPython's global interpreter lock (GIL). This means that
although Python code may be run on any number of threads, only one of those threads will be
executing at any given moment.

The GIL is automatically released whenever Python code calls a Java method or constructor,
allowing Python code to run on other threads while the Java code executes.


Memory management
=================

It's possible to create a cross-language reference cycle if a Python object references a Java
object which, directly or indirectly, references the original Python object. Such a cycle
cannot be detected by the garbage collector in either language. To avoid a memory leak. either
use a weak reference somewhere in the cycle, or break the cycle manually once it's no longer
required.
