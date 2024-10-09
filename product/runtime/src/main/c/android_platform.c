#include <jni.h>
#include <errno.h>
#include <string.h>
#include <android/log.h>
#include <unistd.h>
#include <pthread.h>
#include <stdio.h>

// Adapted from https://github.com/beeware/briefcase-android-gradle-template/blob/v0.3.11/%7B%7B%20cookiecutter.safe_formal_name%20%7D%7D/app/src/main/cpp/native-lib.cpp
// by Asheesh Laroia.
//
// Inspired by https://codelab.wordpress.com/2014/11/03/how-to-use-standard-output-streams-for-logging-in-android-apps/

typedef struct {
    FILE *file;
    int fd;
    android_LogPriority priority;
    char *tag;
    int pipe[2];
} StreamInfo;

// The FILE member can't be initialized here because stdout and stderr are not
// compile-time constants. Instead, it's initialized immediately before the redirection.
static StreamInfo STREAMS[] = {
    {NULL, STDOUT_FILENO, ANDROID_LOG_INFO, "native.stdout", {-1, -1}},
    {NULL, STDERR_FILENO, ANDROID_LOG_WARN, "native.stderr", {-1, -1}},
    {NULL, -1, ANDROID_LOG_UNKNOWN, NULL, {-1, -1}},
};

static void *redirection_thread(void *arg) {
    StreamInfo *si = (StreamInfo*)arg;
    ssize_t read_size;
    char buf[4000];  // Should match MAX_LINE_LEN_BYTES in stream.py.
    while ((read_size = read(si->pipe[0], buf, sizeof buf - 1)) > 0) {
        buf[read_size] = '\0'; /* add null-terminator */
        __android_log_write(si->priority, si->tag, buf);
    }
    return 0;
}

static char *redirect_stream(StreamInfo *si) {
    /* make the FILE unbuffered, to ensure messages are never lost */
    if (setvbuf(si->file, 0, _IONBF, 0)) {
        return "setvbuf";
    }

    /* create the pipe and redirect the file descriptor */
    if (pipe(si->pipe)) {
        return "pipe";
    }
    if (dup2(si->pipe[1], si->fd) == -1) {
        return "dup2";
    }

    /* start the logging thread */
    pthread_t thr;
    if ((errno = pthread_create(&thr, 0, redirection_thread, si))) {
        return "pthread_create";
    }
    if ((errno = pthread_detach(thr))) {
        return "pthread_detach";
    }
    return 0;
}

JNIEXPORT void JNICALL Java_com_chaquo_python_android_AndroidPlatform_redirectStdioToLogcat(
    JNIEnv *env, jobject this
) {
    STREAMS[0].file = stdout;
    STREAMS[1].file = stderr;
    for (StreamInfo *si = STREAMS; si->file; si++) {
        char *error_prefix;
        if ((error_prefix = redirect_stream(si))) {
            char error_message[1024];
            snprintf(error_message, sizeof(error_message),
                     "%s: %s", error_prefix, strerror(errno));
            jclass exc_class = (*env)->FindClass(env, "java/lang/RuntimeException");
            (*env)->ThrowNew(env, exc_class, error_message);
            return;
        }
    }
}
