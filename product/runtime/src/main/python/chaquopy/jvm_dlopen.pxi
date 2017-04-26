import os
import platform
import sys

from . import config

cdef extern from 'dlfcn.h':
    void* dlopen(const char *filename, int flag)
    char *dlerror()
    void *dlsym(void *handle, const char *symbol)
    int dlclose(void *handle)
    unsigned RTLD_LAZY, RTLD_NOW, RTLD_GLOBAL, RTLD_LOCAL, RTLD_DEFAULT, RTLD_NEXT


cdef extern from "jni.h":
    jint JNI_VERSION_1_6
    jboolean JNI_FALSE, JNI_TRUE
    jint JNI_OK, JNI_ERR, JNI_EDETACHED, JNI_EVERSION, JNI_ENOMEM, JNI_EEXIST, JNI_EINVAL
    jint JNI_COMMIT, JNI_ABORT
    ctypedef struct JavaVMInitArgs:
        jint version
        jint nOptions
        jboolean ignoreUnrecognized
        JavaVMOption *options
    ctypedef struct JavaVMOption:
        char *optionString
        void *extraInfo

cdef JNIEnv *_platform_default_env = NULL

cdef void create_jnienv() except *:

    try:
        java_home = os.environ['JAVA_HOME']
    except KeyError:
        raise Exception("JAVA_HOME is not set")
    if not os.path.exists(java_home):
        raise Exception(f"JAVA_HOME ({java_home}) does not exist")
    if os.path.exists(f"{java_home}/jre"):
        jre_home = f"{java_home}/jre"
    else:
        jre_home = java_home

    if sys.platform.startswith("darwin"):  # TODO untested
        lib_path = f"{jre_home}/lib/server/libjvm.dylib"
    elif sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
        lib_path = f"{jre_home}/bin/server/jvm.dll"
    else:  # TODO untested
        machine2cpu = {
            "amd64": "amd64",
            "x86_64": "amd64",
            "arm": "arm",
            "armv7l": "arm",
            "i386": "i386",
            "i686": "i386",
            "x86": "i386",
        }
        lib_path = f"{jre_home}lib/{machine2cpu[platform.machine().lower()]}/server/libjvm.so"

    cdef void *handle = dlopen(str_for_c(lib_path), RTLD_NOW | RTLD_GLOBAL)
    if handle == NULL:
        raise Exception("dlopen: {0}: {1}".format(lib_path, dlerror()))

    cdef void *jniCreateJVM = dlsym(handle, b"JNI_CreateJavaVM")
    if jniCreateJVM == NULL:
       raise Exception("dlfcn: JNI_CreateJavaVM: {0}".format(dlerror()))

    optarr = [str_for_c(opt) for opt in config.options]
    optarr.append(str_for_c("-Djava.class.path=" + config.expand_classpath()))
    cdef JavaVMOption *options = <JavaVMOption*>alloca(sizeof(JavaVMOption) * len(optarr))
    for i, opt in enumerate(optarr):
        options[i].optionString = opt
        options[i].extraInfo = NULL

    cdef JavaVMInitArgs args
    args.version = JNI_VERSION_1_6
    args.options = options
    args.nOptions = len(optarr)
    args.ignoreUnrecognized = JNI_FALSE

    cdef JavaVM* jvm = NULL
    ret = (<jint (*)(JavaVM **pvm, void **penv, void *args)> jniCreateJVM) \
          (&jvm, <void **>&_platform_default_env, &args)
    if ret != JNI_OK:
        raise Exception("JNI_CreateJavaVM failed: {0}".format(ret))

    config.vm_running = True


cdef JNIEnv *get_platform_jnienv() except NULL:
    if _platform_default_env == NULL:
        create_jnienv()
    return _platform_default_env
