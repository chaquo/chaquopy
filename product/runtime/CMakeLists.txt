cmake_minimum_required(VERSION 3.4.1)
project(runtime LANGUAGES C)

# Work around https://github.com/cython/cython/issues/4804.
add_compile_options(-DNDEBUG)

# This warning appears on Python 3.8 only (https://github.com/python/cpython/pull/14193).
add_compile_options(-Wno-deprecated-declarations)

# The Android Gradle plugin may strip libraries before building them into an app, but
# we don't want to require the app developer to have the NDK installed.
set(CMAKE_SHARED_LINKER_FLAGS_RELEASE "${CMAKE_SHARED_LINKER_FLAGS_RELEASE} -s")

include_directories(
    src/main/c
    ${CHAQUOPY_INCLUDE_JAVA})

link_directories(${CHAQUOPY_LIB_DIRS})

if(CHAQUOPY_PYTHON_VERSION)
    set(CHAQUOPY_PYTHON_VERSIONS ${CHAQUOPY_PYTHON_VERSION})
endif()

foreach(VERSION ${CHAQUOPY_PYTHON_VERSIONS})

    set(LIBPYTHON python${VERSION})
    set(INCLUDE_PYTHON ${CHAQUOPY_INCLUDE_PYTHON}/python${VERSION})

    if(CHAQUOPY_PYTHON_VERSION)
        # Single-version mode
        set(CHAQUOPY_MOD chaquopy)
        set(CHAQUOPY_JAVA chaquopy_java)
    else()
        set(CHAQUOPY_MOD chaquopy-${VERSION})
        set(CHAQUOPY_JAVA chaquopy_java-${VERSION})
    endif()

    # Use SHARED rather than MODULE because MODULEs aren't given SONAMEs, which causes
    # runtime warnings on Android.
    add_library(${CHAQUOPY_MOD} SHARED ${CHAQUOPY_SRC_DIR}/chaquopy.c)
    target_include_directories(${CHAQUOPY_MOD} PRIVATE ${INCLUDE_PYTHON})
    target_link_libraries(${CHAQUOPY_MOD} ${LIBPYTHON} dl)
    if(ANDROID)
        target_link_libraries(${CHAQUOPY_MOD} android)  # For native asset API.
    endif()
    set_target_properties(${CHAQUOPY_MOD} PROPERTIES PREFIX "")
    set_target_properties(${CHAQUOPY_MOD} PROPERTIES SUFFIX ${CHAQUOPY_PY_SUFFIX})

    add_library(${CHAQUOPY_JAVA} SHARED ${CHAQUOPY_SRC_DIR}/chaquopy_java.c)
    target_include_directories(${CHAQUOPY_JAVA} PRIVATE ${INCLUDE_PYTHON})
    target_link_libraries(${CHAQUOPY_JAVA} ${LIBPYTHON})
    if(ANDROID)
        target_sources(${CHAQUOPY_JAVA} PRIVATE src/main/c/android_platform.c)
        target_link_libraries(${CHAQUOPY_JAVA} log)
    elseif(WIN32)
        # System.loadLibary expects a "lib" prefix on Unix, but not on Windows.
        set_target_properties(${CHAQUOPY_JAVA} PROPERTIES PREFIX "")
    endif()
endforeach()
