// The module initialization function in the generated C file is further down the file than the
// place from where it's called, so "extern from *" isn't good enough.

#if PY_MAJOR_VERSION < 3
PyMODINIT_FUNC initchaquopy_java(void);
#else
PyMODINIT_FUNC PyInit_chaquopy_java(void);
#endif
