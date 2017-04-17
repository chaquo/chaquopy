#ifdef __ANDROID__
// Crystax's pyconfig_x86.h indicates this header is available, but it isn't included in
// the stock NDK. The header's actual content is not required.
#else
#include_next "ieeefp.h"
#endif