cmake_minimum_required(VERSION 3.4.1)

add_library(
    repl SHARED
    src/main/jni/com_chaquo_python_demo_Repl.cpp
    src/main/jni/repl.c
)
target_link_libraries(repl python2.7)

add_library(
    python2.7 SHARED IMPORTED
)
set_target_properties(
    python2.7 PROPERTIES
    IMPORTED_LOCATION ${CMAKE_SOURCE_DIR}/prebuilt/libs/${ANDROID_ABI}/libpython2.7.so
)
include_directories(prebuilt/include/python)
