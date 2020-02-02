cmake_minimum_required(VERSION 3.4.1)
project(runtime LANGUAGES C)

# This warning appears on Python 3.8 only (https://github.com/python/cpython/pull/14193).
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wno-deprecated-declarations")

set(CMAKE_SHARED_LINKER_FLAGS_RELEASE "${CMAKE_SHARED_LINKER_FLAGS_RELEASE} -s")

include_directories(
    src/main/c
    ${CHAQUOPY_INCLUDE_DIRS})

if(CHAQUOPY_LIB_DIRS)
    link_directories(${CHAQUOPY_LIB_DIRS})
endif()

# Use SHARED rather than MODULE because MODULEs aren't given SONAMEs, which causes warnings on
# Android (#5582).
add_library(chaquopy SHARED ${CHAQUOPY_SRC_DIR}/chaquopy.c)
target_link_libraries(chaquopy ${CHAQUOPY_LIBS} dl)  # On MSYS2, libdl is in the "dlfcn" package.
set_target_properties(chaquopy PROPERTIES PREFIX "${PY_LIB_PREFIX}")
set_target_properties(chaquopy PROPERTIES SUFFIX "${PY_LIB_SUFFIX}")

add_library(chaquopy_java SHARED ${CHAQUOPY_SRC_DIR}/chaquopy_java.c)
target_link_libraries(chaquopy_java ${CHAQUOPY_LIBS})
set_target_properties(chaquopy_java PROPERTIES PREFIX "${JAVA_LIB_PREFIX}")
set_target_properties(chaquopy_java PROPERTIES SUFFIX "${JAVA_LIB_SUFFIX}")

if(ANDROID)
    add_library(chaquopy_android SHARED ${CHAQUOPY_SRC_DIR}/chaquopy_android.c)
    target_link_libraries(chaquopy_android ${CHAQUOPY_LIBS} android)
    set_target_properties(chaquopy_android PROPERTIES PREFIX "${PY_LIB_PREFIX}")
    set_target_properties(chaquopy_android PROPERTIES SUFFIX "${PY_LIB_SUFFIX}")
endif()
