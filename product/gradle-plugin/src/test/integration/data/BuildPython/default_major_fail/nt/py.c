// /mingw64/bin/cc py.c -s -o py.exe

#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[])
{
    if (strcmp(argv[2], "-m") != 0) {
        printf("python%s was probed\n", argv[1] + 1);
        return 1;
    } else {
        printf("python%s was used\n", argv[1] + 1);
        return 1;
    }
}
