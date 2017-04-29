import os
import platform
import sys

from . import config  # Don't import reflect here, it causes a circular reference

from libc.stdint cimport uintptr_t


cdef extern from 'dlfcn.h':
    void* dlopen(const char *filename, int flag)
    char *dlerror()
    void *dlsym(void *handle, const char *symbol)
    int dlclose(void *handle)
    unsigned RTLD_LAZY, RTLD_NOW, RTLD_GLOBAL, RTLD_LOCAL, RTLD_DEFAULT, RTLD_NEXT


cdef JavaVM *jvm = NULL

cdef JNIEnv *get_jnienv() except NULL:
    if jvm == NULL:
        set_jvm(start_jvm())
        # Prevent the Java module from trying to start Python
        # FIXME add test that this works (requires static field set)
        from . import reflect
        reflect.autoclass("com.chaquo.python.Python").started = True

    cdef JNIEnv *env = NULL
    jvm[0].AttachCurrentThread(jvm, <void**>&env, NULL)
    return env


cdef void set_jvm(JavaVM *new_jvm):
    global jvm
    jvm = new_jvm
    config.vm_running = True


cdef JavaVM *start_jvm() except NULL:
    lib_path = jvm_lib_path()
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
    cdef JNIEnv *env = NULL
    ret = (<jint (*)(JavaVM **pvm, void **penv, void *args)> jniCreateJVM) \
          (&jvm, <void **>&env, &args)
    if ret != JNI_OK:
        raise Exception("JNI_CreateJavaVM failed: {0}".format(ret))

    return jvm


def jvm_lib_path():
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
        return f"{jre_home}/lib/server/libjvm.dylib"
    elif sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
        return f"{jre_home}/bin/server/jvm.dll"
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
        return f"{jre_home}lib/{machine2cpu[platform.machine().lower()]}/server/libjvm.so"


def detach():
    jvm[0].DetachCurrentThread(jvm)
