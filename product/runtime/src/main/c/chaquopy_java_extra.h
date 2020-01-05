// Cython generates a chaquopy_java.h automatically, so we need to use a different name.

#include "Python.h"


// The module initialization function in the generated C file is further down the file than the
// place from where it's called, so "extern from *" isn't good enough.
PyMODINIT_FUNC PyInit_chaquopy_java(void);
