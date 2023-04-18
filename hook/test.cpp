#include <windows.h>
#include "detours.h"

#pragma comment(lib, "D:\\VSCode\\GP\\hook\\detours_x86.lib")

void hook() {
    
}

int main(int argc, char **args)
{
    OutputDebugString("AAAAAAAAAAA");
}