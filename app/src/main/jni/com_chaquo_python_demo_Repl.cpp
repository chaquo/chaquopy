#include <cstdio>
#include <cassert>
#include <string>
using namespace std;

#include <jni.h>
#include <Python.h>

#include "repl.h"


static string fromJstring (JNIEnv *env, jstring jstr)
{
    string str;
    const char *bytes = env->GetStringUTFChars (jstr, NULL);
    if (bytes) {
        str = string (bytes);
        env->ReleaseStringUTFChars (jstr, bytes);
    } else {
        fprintf(stderr, "GetStringUTFChars failed\n");
    }
    return str;
}

static jstring toJstring (JNIEnv *env, const char *str)
{
    return env->NewStringUTF (str);
}
static jstring toJstring (JNIEnv *env, const string &str)
{
    return toJstring(env, str.c_str());
}


struct State {
    bool started;
};


static State *getState(JNIEnv *env, jobject instance) {
    jclass cRepl = env->FindClass("com/chaquo/python/demo/Repl");
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

// This isn't in standard Python 2, but is in the Crystax version (though they neglected to add it to
// the API headers as well).
//
// FIXME: In Python 3, this takes a wchar_t* !
PyAPI_FUNC(void) Py_SetPath(char *path);

JNIEXPORT void JNICALL
Java_com_chaquo_python_demo_Repl_nativeStart(JNIEnv *env, jobject instance, jstring path) {
    State *state = getState(env, instance);

    if (! state->started) {
        // FIXME: In Python 3, these functions both take wchar_t* strings!
        Py_SetProgramName((char*)"chaquo_python");
        Py_SetPath((char*) fromJstring(env, path).c_str());

        Py_Initialize();

        #if PY_MAJOR_VERSION < 3
        initrepl();
        #else
        PyInit_repl();
        #endif

        state->started = true;
    }
}

JNIEXPORT void JNICALL
Java_com_chaquo_python_demo_Repl_nativeStop(JNIEnv *env, jobject instance) {
    State *state = getState(env, instance);
    if (state->started) {
        Py_Finalize();
        state->started = false;
    }
}

JNIEXPORT jstring JNICALL
Java_com_chaquo_python_demo_Repl_exec(JNIEnv *env, jobject instance, jstring line_js) {
    PyObject *line_py = PyString_FromString(fromJstring(env, line_js).c_str());
    PyObject *result_py = repl_exec(line_py);
    Py_DECREF(line_py);

    if (result_py == NULL) {
        return toJstring(env, "repl_get_output failed");
    }
    jstring result_js = toJstring(env, PyString_AsString(result_py));
    Py_DECREF(result_py);
    return result_js;
}

}