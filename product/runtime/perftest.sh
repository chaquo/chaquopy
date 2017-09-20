#!/bin/bash -e
export CLASSPATH='C:\Users\smith\cygwin\git\chaquo\python\product\runtime\build\classes\main;C:\Users\smith\cygwin\git\chaquo\python\product\runtime\build\classes\test;C:\Users\smith\Programs\android-sdk/platforms/android-23/android.jar'
export PYTHONPATH='C:\Users\smith\cygwin\git\chaquo\python\product\runtime/src/main/python;C:\Users\smith\cygwin\git\chaquo\python\product\runtime/src/test/python'
export PATH="C:\Users\smith\cygwin\git\chaquo\python\product\runtime\build/cmake/2.7/host;$PATH"

cls="android.view.View"
method="getWidth"
field="FOCUS_DOWN"
nested="OnClickListener"
python2.7.exe -m timeit -n1 \
    "import java" \
    "cls = java.jclass('$cls')" \
    "print cls.$method" \
    "print cls.$field" \
    "print cls.$nested" \
    "del java.chaquopy.jclass_cache['$cls']"
