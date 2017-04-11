#ifndef JNI_WRAPPERS_H
#define JNI_WRAPPERS_H

// Adapted from JNITL

#include <jni.h>
#include <assert.h>


class JString {
private:
	JNIEnv* const	env;
	const jstring	jstr;
	char *	psz;
public:
	JString( JNIEnv* _env, const jstring str ) : jstr(str),env(_env) {
		psz = (char*) env->GetStringUTFChars(jstr, NULL);
		assert(psz);
	}
	~JString() {
		env->ReleaseStringUTFChars(jstr, psz);
	}

	operator char *() const {
		return psz;
	}
};


template <typename T/*something that derives from jobject*/>
class GlobalRef {
private:
	T obj;
	JNIEnv* env;

public:
	GlobalRef(JNIEnv* env, T obj) : obj(NULL), env(NULL) {
		Attach(env,obj);
	}
	GlobalRef() : obj(NULL),env(NULL) {}
	~GlobalRef() {
		Detach();
	}
	void Attach(JNIEnv* _env, T _obj) {
		Detach();
		env = _env;
		obj = env->NewGlobalRef(_obj);
	}
	void Detach() {
		if(obj!=NULL) {
			env->DeleteGlobalRef(obj);
			obj = NULL;
		}
	}
	operator T () {
		return obj;
	}
};

#endif // JNI_WRAPPERS_H