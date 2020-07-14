// Cython generates a chaquopy_java.h automatically, so we need to use a different name.

#include "Python.h"


// The chaquopy_java library isn't loaded like a normal Python module. Instead, it's loaded
// from Java using System.loadLibrary. The Java code then calls Python.startNative, which calls
// PyInit_chaquopy_java. This is all much easier if we use single-phase initialization.
#undef CYTHON_PEP489_MULTI_PHASE_INIT
#define CYTHON_PEP489_MULTI_PHASE_INIT 0

// The module initialization function in the generated C file is further down the file than the
// place from where it's called, so we need to provide a prototype.
PyMODINIT_FUNC PyInit_chaquopy_java(void);
