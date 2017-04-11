cmake_minimum_required(VERSION 3.4.1)

include_directories(src/main/cpp)

add_library(
    chaquo SHARED
    src/main/cpp/Python.cpp
    # TODO Cython output files
)
target_link_libraries(chaquo python)

add_library(
    python SHARED IMPORTED
)
set_target_properties(
    python PROPERTIES
    IMPORTED_LOCATION "${CRYSTAX_PYTHON}/${PYTHON_VERSION}/libs/${ANDROID_ABI}/\
libpython${PYTHON_VERSION}${PYTHON_ABI_FLAGS}.so"
)
include_directories(${CRYSTAX_PYTHON}/${PYTHON_VERSION}/include/python)
