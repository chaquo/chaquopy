#ifdef _WIN32  // Also defined on 64-bit
// alloca is defined in malloc.h on MSYS2.
#include "malloc.h"
#else
#include_next "alloca.h"
#endif
