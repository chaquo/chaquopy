cmake_minimum_required(VERSION 3.4.1)
project(runtime LANGUAGES C)

include_directories(
    src/main/c          # For ieeefp.h
    ${CHAQUOPY_INCLUDE_DIRS})

if(CHAQUOPY_LIB_DIRS)
    link_directories(${CHAQUOPY_LIB_DIRS})
endif()

add_library(jnius MODULE
    build/cython/jnius.c)

target_link_libraries(jnius ${CHAQUOPY_LIBS})

set_target_properties(jnius PROPERTIES PREFIX "")
if(CHAQUOPY_SUFFIX)
    set_target_properties(jnius PROPERTIES SUFFIX ${CHAQUOPY_SUFFIX})
endif()
