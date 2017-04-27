import os
import platform
import sys

from . import config

from jni cimport *
from libc.stdint cimport uintptr_t


cdef extern from 'dlfcn.h':
    void* dlopen(const char *filename, int flag)
    char *dlerror()
    void *dlsym(void *handle, const char *symbol)
    int dlclose(void *handle)
    unsigned RTLD_LAZY, RTLD_NOW, RTLD_GLOBAL, RTLD_LOCAL, RTLD_DEFAULT, RTLD_NEXT


cdef JavaVM *jvm = NULL

cdef JNIEnv *get_jnienv() except NULL:
    global jvm
    if jvm == NULL:
        jvm = start_jvm()

    cdef JNIEnv *env = NULL
    jvm[0].AttachCurrentThread(jvm, <void**>&env, NULL)
    return env


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

    config.vm_running = True
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


# TODO create base class JNIRef, which would contain the common behaviour (including __nonzero__,
# __repr__ and telem), and facilitate the JNI interface layer mentioned above.

# FIXME should be called GlobalRef
cdef class LocalRef(object):
    cdef jobject obj

    def __init__(self):
        telem[self.__class__.__name__] += 1

    def __dealloc__(self):
        cdef JNIEnv *j_env
        if self.obj != NULL:
            j_env = get_jnienv()
            j_env[0].DeleteGlobalRef(j_env, self.obj)
        self.obj = NULL
        telem[self.__class__.__name__] -= 1

    # FIXME use same approach as LocalActualRef
    cdef void create(self, JNIEnv *env, jobject obj):
        self.obj = env[0].NewGlobalRef(env, obj)

    def __repr__(self):
        return '<LocalRef obj=0x{0:x} at 0x{1:x}>'.format(
            <uintptr_t>self.obj, id(self))

    def __nonzero__(self):
        return self.obj != NULL


# FIXME use same approach as LocalActualRef
cdef LocalRef create_local_ref(JNIEnv *env, jobject obj):
    cdef LocalRef ret = LocalRef()
    ret.create(env, obj)
    return ret


# FIXME should be called LocalRef. Named to facilitate future search and replace.
cdef class LocalActualRef(object):
    # It's safe to store j_env, as long as the LocalActualRef isn't kept beyond the thread detach
    # or Java "native" method return.
    cdef JNIEnv *env
    cdef jobject obj

    def __init__(self):
        telem[self.__class__.__name__] += 1

    # Constructors can't take C pointer arguments
    @staticmethod
    cdef LocalActualRef create(JNIEnv *env, jobject obj):
        cdef LocalActualRef lr = LocalActualRef()
        lr.env = env
        lr.obj = obj
        return lr

    def __dealloc__(self):
        if self.obj:
            self.env[0].DeleteLocalRef(self.env, self.obj)
        self.obj = NULL
        telem[self.__class__.__name__] -= 1

    cdef LocalRef global_ref(self):
        return create_local_ref(self.env, self.obj)

    def __repr__(self):
        return '<LocalActualRef obj=0x{0:x} at 0x{1:x}>'.format(
            <uintptr_t>self.obj, id(self))

    def __nonzero__(self):
        return self.obj != NULL
