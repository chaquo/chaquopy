cmake_minimum_required(VERSION 3.4.1)
project(runtime LANGUAGES C)

add_library(jnius MODULE
    src/main/c/Python.c
    build/cython/jnius.c
)
set_target_properties(jnius PROPERTIES
    PREFIX ""
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/src/main/python/jnius
)
target_include_directories(jnius PRIVATE
    src/main/c          # For ieeefp.h and jni.h
    "${PYTHON_INCLUDE}"
)
target_link_libraries(jnius "${PYTHON_LIB}" "${JDK_HOME}/jre/bin/server/jvm.dll")
