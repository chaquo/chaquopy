// See https://igraph.org/c/html/latest/igraph-Installation.html. Although that page
// says the following settings are for macOS, running arithchk on Android returns the
// same values, according to
// https://github.com/chaquo/chaquopy/pull/1196#discussion_r1825264094.

// f2c requires this setting even on ARM64.
#define IEEE_8087

#define Arith_Kind_ASL 1
#define Long int
#define Intcast (int)(long)
#define Double_Align
#define X64_bit_pointers
#define NANCHECK
#define QNaN0 0x0
#define QNaN1 0x7ff80000
