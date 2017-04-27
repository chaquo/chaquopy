from jni cimport *
from libc.stdio cimport printf

# FIXME all Java API functions which may touch the Python VM must be "with gil"

cdef public jint JNI_OnLoad(JavaVM *jvm, void *reserved):
    return JNI_VERSION_1_6

cdef public void Java_com_chaquo_python_Python_start(JNIEnv *env, jstring pythonPath):
    if pythonPath != NULL:
        pass    # FIXME

cdef public jstring Java_com_chaquo_python_Python_hello(JNIEnv *env, jstring str):
    # FIXME need string conversion for both input and output
    return NULL

cdef public jint Java_com_chaquo_python_Python_add(JNIEnv *env, jobject this, jint x):
    return x + 42


# // This isn't in the standard Python 2 API, but is in the Crystax version (though they neglected to
# // add it to the API headers as well).
# //
# // FIXME: In Python 3, this takes a wchar_t* !
# PyAPI_FUNC(void) Py_SetPath(char *path);

# // FIXME If this is a Python process, do not do any of this: it has already been done by the
# // Python executable, except for PyEval_InitThreads(), which FIXME has been done by the Python
# // part of the runtime.
# JNIEXPORT void JNICALL
# Java_com_chaquo_python_Python_start(JNIEnv *env, jobject instance, jstring stdlibFilename) {
#     // FIXME: In Python 3, these functions both take wchar_t* strings!
#     Py_SetProgramName((char*)"chaquopy");
#     // FIXME only works in Crystax: use PYTHONPATH instead
#     // Py_SetPath(JString(env, stdlibFilename));

#     Py_Initialize();
#     PyEval_InitThreads();

#     // FIXME load Python part of runtime and pass it our JNIEnv before it has a chance to try and
#     // start a Java VM itself.

# }
