// /mingw64/bin/cc python.c -s -o python.exe

#include <stdio.h>
#include <string.h>


int main(int argc, char *argv[])
{
    if (strcmp(argv[1], "--version") == 0) {
        return 0;
    } else {
        printf("Versionless executable was used\n");
        return 1;
    }
}
