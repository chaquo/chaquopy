// /mingw64/bin/cc py.c -s -o py.exe

#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[])
{
    int major = (strcmp(argv[1], "-3") == 0);
    if (strcmp(argv[2], "--version") == 0) {
        return major ? 0 : 1;
    } else {
        printf("%s version was used\n", major ? "Major" : "Minor");
        return 1;
    }
}
