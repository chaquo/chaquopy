// /mingw64/bin/cc python.c -s -o python.exe

#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[])
{
    if (strcmp(argv[1], "-m") != 0) {
        printf("python was probed\n");
        return 1;
    } else {
        printf("python was used\n");
        return 1;
    }
}
