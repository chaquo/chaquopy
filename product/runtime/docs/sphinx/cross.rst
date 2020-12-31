Cross-language issues
#####################


.. _cross-multi-threading:

Multi-threading
===============

Chaquopy is thread-safe. However, because it's based on CPython (the Python reference
implementation), it is limited by CPython's global interpreter lock (GIL). This means that
although Python code may be run on any number of threads, only one of those threads will be
executing at any given moment.

The GIL can be a bottleneck for threads which release and acquire it many times in quick
succession (`see discussion here <https://bugs.python.org/issue7946>`_). If your UI thread
makes many Python calls while a CPU-bound Python thread is running in the background, you may
improve responsiveness by reducing :any:`sys.setswitchinterval` from its default value of 0.005
to something lower like 0.001.

:any:`threading.main_thread` will return the thread on which Python was started. Depending on
your app's structure, this might not be the same as the main thread in Java.

.. seealso:: The :ref:`multi-threading features <python-multi-threading>` of the Python API.


Memory management
=================

It's possible to create a cross-language reference cycle if a Python object references a Java
object which, directly or indirectly, references the original Python object. Such a cycle
cannot be detected by the garbage collector in either language. To avoid a memory leak. either
use a weak reference somewhere in the cycle, or break the cycle manually once it's no longer
required.
