We patch pandas to extract the NumPy C API headers from a wheel file. You must therefore set
the following environment variable giving the prefix of the wheel filename:

   CHAQUOPY_NUMPY_PREFIX=/path/to/numpy-A.B.C-D

The remainder of the filename will be filled in from the CHAQUOPY_COMPAT_TAG environment
variable, set by build-wheel.py.
