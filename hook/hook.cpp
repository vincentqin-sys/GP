#include <windows.h>
#include <stdio.h>
#include "detours.h"

#pragma comment(lib, "D:\\VSCode\\GP\\hook\\detours_x86.lib")

void load();
void unload();

static BOOL(WINAPI *TrueTextOut)(HDC hdc, int nXStart, int nYStart, LPCSTR lpString, int cchString) = TextOut;
static int(WINAPI *TrueDrawText)(HDC hdc, LPCTSTR lpchText, int nCount, LPRECT lpRect, UINT uFormat) = DrawText;
static BOOL(WINAPI *TrueExtTextOut)(HDC hdc, int x, int y, UINT options, CONST RECT *lprect, LPCSTR lpString, UINT c, CONST INT *lpDx) = ExtTextOut;
static BOOL (WINAPI *TruePolyTextOut)( HDC hdc, CONST POLYTEXTA *ppt,  int nstrings) = PolyTextOut;
int (WINAPI * TrueDrawTextEx)(  HDC hdc, LPSTR lpchText,  int cchText,  LPRECT lprc,  UINT format,  LPDRAWTEXTPARAMS lpdtp) =  DrawTextEx;

extern "C" int APIENTRY
DllMain(HINSTANCE hins, DWORD reason, LPVOID release)
{
    if (reason == DLL_PROCESS_ATTACH) {
        load();
    } else if (reason == DLL_PROCESS_DETACH) {
        unload();
    }
    else if (reason == DLL_THREAD_ATTACH) {

    }
    else if (reason == DLL_THREAD_DETACH) {

    }
    return 1;
}

BOOL WINAPI NewTextOut(HDC hdc, int x, int y, LPCSTR lpString, int cchString)
{
    BOOL b = TrueTextOut(hdc, x, y, lpString, cchString);
    static char tmp[1024];
    sprintf(tmp , "Call TextOut:  (%d, %d) %s", x, y, lpString);
    OutputDebugString(tmp);
    return b;
}

int WINAPI NewDrawText(HDC hdc, LPCTSTR lpchText, int nCount, LPRECT lpRect, UINT uFormat)
{
    int b = TrueDrawText(hdc, lpchText, nCount, lpRect, uFormat);
    static char tmp[1024];
    sprintf(tmp, "Call DrawText:  %s", lpchText);
    OutputDebugString(tmp);
    return b;
}

BOOL WINAPI NewExtTextOut(HDC hdc, int x, int y, UINT options, CONST RECT *lprect, LPCSTR lpString, UINT c, CONST INT *lpDx) {
    static char tmp[1024];
    sprintf_s(tmp, 1000, "Call NewExtTextOut:  %s", lpString);
    return TrueExtTextOut(hdc, x, y, options, lprect, lpString, c, lpDx);
}

int WINAPI NewDrawTextEx(HDC hdc, LPSTR lpchText, int cchText, LPRECT lprc, UINT format, LPDRAWTEXTPARAMS lpdtp)
{
    static char tmp[1024];
    sprintf_s(tmp, 1000, "Call NewDrawTextEx:  %s", lpchText);
    return TrueDrawTextEx(hdc, lpchText, cchText, lprc, format, lpdtp);
}

BOOL WINAPI NewPolyTextOut(HDC hdc, CONST POLYTEXTA *ppt, int nstrings) {
    static char tmp[1024];
    sprintf_s(tmp, 1000, "Call NewPolyTextOut:  %s", ppt->lpstr);
    return TruePolyTextOut(hdc, ppt, nstrings);
}

void load()
{
    DetourRestoreAfterWith();
    DetourTransactionBegin();
    DetourUpdateThread(GetCurrentThread());
    DetourAttach(&(PVOID &)TrueDrawText, NewDrawText);
    DetourAttach(&(PVOID &)TrueDrawTextEx, NewDrawTextEx);
    DetourAttach(&(PVOID &)TrueTextOut, NewTextOut);
    DetourAttach(&(PVOID &)TrueExtTextOut, NewExtTextOut);
    DetourAttach(&(PVOID &)TruePolyTextOut, NewPolyTextOut);

    int error = DetourTransactionCommit();
    if (error == NO_ERROR) {
        OutputDebugString("Hook my hook" DETOURS_STRINGIFY(DETOURS_BITS) ".dll:  Detoured OK");
    }
    else {
        char tmp[100];
        sprintf(tmp, "Hook my hook" DETOURS_STRINGIFY(DETOURS_BITS) ".dll: Detoured Fail  %d", error);
        OutputDebugString(tmp);
    }
}

void unload()
{
    DetourTransactionBegin();
    DetourUpdateThread(GetCurrentThread());
    DetourDetach(&(PVOID &)TrueDrawText, NewDrawText);
    DetourDetach(&(PVOID &)TrueDrawTextEx, NewDrawTextEx);
    DetourDetach(&(PVOID &)TrueTextOut, NewTextOut);
    DetourDetach(&(PVOID &)TrueExtTextOut, NewExtTextOut);
    DetourDetach(&(PVOID &)TruePolyTextOut, NewPolyTextOut);
    DetourTransactionCommit();
    OutputDebugString("uload my hook");
}