// /mingw64/bin/cc py.c -s -o py.exe

#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[])
{
    if (strcmp(argv[2], "--version") == 0) {
        return 0;
    } else {
        printf("%s was used\n", argv[1] + 1);
        return 1;
    }
}
