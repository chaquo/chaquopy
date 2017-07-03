// Cython generates a chaquopy_java.h automatically, so we need to use a different name.

#include "Python.h"


// The module initialization function in the generated C file is further down the file than the
// place from where it's called, so "extern from *" isn't good enough.
#if PY_MAJOR_VERSION < 3
PyMODINIT_FUNC initchaquopy_java(void);
#define PyInit_chaquopy_java initchaquopy_java
#else
PyMODINIT_FUNC PyInit_chaquopy_java(void);
#endif


#if __ANDROID__ && PY_MAJOR_VERSION < 3
// Py_SetPath isn't in the standard CPython API until Python 3. But the Crystax build of Python
// 2.7 has been modified to add it, and it *must* be called (PYTHONPATH has no effect),
// otherwise Py_Initialize will call abort(). They still neglected to add it to their header
// files, though, so we need to declare it here.
//
// NOTE: In Python 3, Py_SetPath takes a wchar_t* string.
//
// ", 1" makes the call evaluate to true, for compatibility with set_path_env.
PyAPI_FUNC(void) Py_SetPath(char *path);
#define set_path(env, python_path) (Py_SetPath((char*)(python_path)), 1)
#else
// Call function defined in chaquopy_java.pyx
#define set_path set_path_env
#endif
