#ifdef __CYGWIN__

#include <stdint.h>

// Microsoft compiler definition
#define __int64 int64_t

// On x86-64, long is 32 bits with Microsoft compilers (which the Oracle Windows JDK headers are
// written for) but 64 bits with Cygwin gcc. (int is 32 bits in both cases.)
#define long int32_t
#include "jni_md.h"
#undef long

#endif // __CYGWIN__

#include_next "jni.h"
