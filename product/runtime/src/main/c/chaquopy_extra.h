// See comment in jni.pxd.
#if __ANDROID__
#define Attach_JNIEnv JNIEnv
#else
#define Attach_JNIEnv void
#endif
