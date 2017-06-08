#!/bin/bash
set -e
export CLASSPATH='C:\Users\smith\cygwin\git\chaquo\python\product\runtime\build\classes\main;C:\Users\smith\cygwin\git\chaquo\python\product\runtime\build\classes\test'
export PYTHONPATH='C:\Users\smith\cygwin\git\chaquo\python\product\runtime/src/main/python;C:\Users\smith\cygwin\git\chaquo\python\product\runtime/src/test/python'
export PATH="C:\Users\smith\cygwin\git\chaquo\python\product\runtime\build/cmake/2.7/host;$PATH"
winpty python2.7.exe
