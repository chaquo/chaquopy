#include <jni.h>
#include <Python.h>

#include <assert.h>

#include "jni_wrappers.h"

struct State {
    bool started;
};


static State *getState(JNIEnv *env, jobject instance) {
    jclass cRepl = env->FindClass("com/chaquo/python/Python");
    jfieldID fNativeState = env->GetFieldID(cRepl, "nativeState", "J");
    jlong lState = env->GetLongField(instance, fNativeState);
    if (lState == 0) {
        State *state = new State();
        env->SetLongField(instance, fNativeState, (jlong)state);
        return state;
    } else {
        return (State*)lState;
    }
}

extern "C" {

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm, void* reserved)
{
    JNIEnv* env = NULL;
    if (vm->GetEnv((void**) &env, JNI_VERSION_1_4) != JNI_OK) {
        fprintf(stderr, "GetEnv failed\n");
        return -1;
    }
    assert(env != NULL);
    return JNI_VERSION_1_4;
}

// This isn't in the standard Python 2 API, but is in the Crystax version (though they neglected to
// add it to the API headers as well).
//
// FIXME: In Python 3, this takes a wchar_t* !
PyAPI_FUNC(void) Py_SetPath(char *path);

JNIEXPORT void JNICALL
Java_com_chaquo_python_Python_startPython(JNIEnv *env, jobject instance, jstring stdlibFilename) {
    // FIXME: In Python 3, these functions both take wchar_t* strings!
    Py_SetProgramName((char*)"chaquo_python");
    Py_SetPath(JString(env, stdlibFilename));
    Py_Initialize();

    /* FIXME
    #if PY_MAJOR_VERSION < 3
    initrepl();
    #else
    PyInit_repl();
    #endif
    */
}

JNIEXPORT void JNICALL
Java_com_chaquo_python_demo_Repl_nativeStop(JNIEnv *env, jobject instance) {
    State *state = getState(env, instance);
    if (state->started) {
        Py_Finalize();
        state->started = false;
    }
}

}