#include <cstdio>
#include <cassert>
#include <string>
using namespace std;

#include <jni.h>
#include <Python.h>

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

// This isn't in standard Python 2, but is in the Crystax build (though they neglected to add it to
// the API headers as well).
//
// WARNING: In Python 3, this takes a wchar_t* !
PyAPI_FUNC(void) Py_SetPath(char *path);

JNIEXPORT void JNICALL
Java_com_chaquo_python_demo_Repl_nativeStart(JNIEnv *env, jobject instance, jstring jAssetsDir) {
    State *state = getState(env, instance);
    string assetsDir = fromJstring(env, jAssetsDir);

    if (! state->started) {
        // WARNING: In Python 3, these functions both take wchar_t* strings!
        Py_SetProgramName((char*)"chaquo_python");
        Py_SetPath((char*) (assetsDir + "/stdlib.zip").c_str()); // FIXME use final field

        Py_Initialize();
        FILE *startFile = fopen((assetsDir + "/start.py").c_str(), "r"); // FIXME use final field
        if (startFile == NULL) {
            return; // FIXME
        }
        if (PyRun_SimpleFileEx(startFile, NULL, true) != 0) {
            return; // FIXME
        }
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
Java_com_chaquo_python_demo_Repl_eval(JNIEnv *env, jobject instance, jstring expr) {


    PyRun_SimpleString(fromJstring(env, expr).c_str());


    // FIXME



    PyObject *module = PyImport_AddModule("__main__");
    if (module == NULL) {
        return toJstring(env, "PyImport_AddModule failed");
    }
    PyObject *dict = PyModule_GetDict(module);

    PyObject *result_obj = PyRun_String(
                                        Py_single_input, dict, dict);
    if (result_obj == NULL) {
        PyErr_Print();
        return toJstring(env, "EXCEPTION");
    }

    PyObject *result_repr = PyObject_Repr(result_obj);
    Py_DECREF(result_obj);
    if (result_repr == NULL) {
        return toJstring(env, "PyObject_Repr failed");
    }
    jstring result_jstr = toJstring(env, PyString_AsString(result_repr));
    Py_DECREF(result_repr);
    return result_jstr;
}

}