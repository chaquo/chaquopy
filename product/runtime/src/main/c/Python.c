#include <jni.h>
#include <Python.h>

#include <assert.h>


JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm, void* reserved)
{
    return JNI_VERSION_1_4;
}

// This isn't in the standard Python 2 API, but is in the Crystax version (though they neglected to
// add it to the API headers as well).
//
// FIXME: In Python 3, this takes a wchar_t* !
PyAPI_FUNC(void) Py_SetPath(char *path);

JNIEXPORT void JNICALL
Java_com_chaquo_python_Python_start(JNIEnv *env, jobject instance, jstring stdlibFilename) {

    // FIXME: In Python 3, these functions both take wchar_t* strings!
    Py_SetProgramName((char*)"chaquopy");
    // FIXME not in Cygwin
    // Py_SetPath(JString(env, stdlibFilename));

    Py_Initialize();
}

JNIEXPORT void JNICALL
Java_com_chaquo_python_Python_stop(JNIEnv *env, jobject instance) {
    Py_Finalize();
}
