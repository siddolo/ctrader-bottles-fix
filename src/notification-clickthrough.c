#define UNICODE
#define _UNICODE
#include <windows.h>

static const WCHAR mutex_name[] = L"Local\\cTraderOverlayFix";
static const WCHAR stop_name[] = L"Local\\cTraderOverlayFixStop";

static BOOL contains(const WCHAR *text, const WCHAR *needle)
{
    for (; *text; ++text)
    {
        const WCHAR *a = text, *b = needle;
        while (*a && *b && *a == *b) { ++a; ++b; }
        if (!*b) return TRUE;
    }
    return FALSE;
}

static WCHAR lower(WCHAR ch)
{
    return ch >= L'A' && ch <= L'Z' ? ch + (L'a' - L'A') : ch;
}

static BOOL is_ctrader(DWORD pid)
{
    WCHAR path[1024];
    DWORD length = sizeof(path) / sizeof(path[0]);
    HANDLE process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (!process) return FALSE;
    BOOL found = QueryFullProcessImageNameW(process, 0, path, &length);
    CloseHandle(process);
    if (!found || !length || length >= sizeof(path) / sizeof(path[0])) return FALSE;
    path[length] = 0;
    const WCHAR *name = path;
    for (const WCHAR *p = path; *p; ++p)
        if (*p == L'\\' || *p == L'/') name = p + 1;
    const WCHAR *expected = L"cTrader.exe";
    while (*name && *expected && lower(*name) == lower(*expected)) { ++name; ++expected; }
    return !*name && !*expected;
}

static BOOL CALLBACK fix_overlay(HWND hwnd, LPARAM unused)
{
    WCHAR cls[256];
    DWORD pid = 0;
    (void)unused;
    if (!GetClassNameW(hwnd, cls, sizeof(cls) / sizeof(cls[0])) ||
        !contains(cls, L"HwndWrapper[") || !contains(cls, L"Popup Notifications Thread"))
        return TRUE;
    GetWindowThreadProcessId(hwnd, &pid);
    if (!is_ctrader(pid)) return TRUE;
    LONG_PTR style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
    if (!(style & WS_EX_LAYERED) || (style & WS_EX_TRANSPARENT)) return TRUE;
    SetLastError(0);
    if (!SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT) && GetLastError())
        return TRUE;
    SetWindowPos(hwnd, NULL, 0, 0, 0, 0,
                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE |
                 SWP_FRAMECHANGED | SWP_ASYNCWINDOWPOS);
    return TRUE;
}

void mainCRTStartup(void)
{
    const WCHAR *command = GetCommandLineW();
    if (contains(command, L"--stop"))
    {
        HANDLE event = OpenEventW(EVENT_MODIFY_STATE, FALSE, stop_name);
        if (event) { SetEvent(event); CloseHandle(event); }
        ExitProcess(0);
    }
    if (contains(command, L"--once"))
    {
        EnumWindows(fix_overlay, 0);
        ExitProcess(0);
    }
    HANDLE mutex = CreateMutexW(NULL, FALSE, mutex_name);
    if (!mutex) ExitProcess(1);
    if (GetLastError() == ERROR_ALREADY_EXISTS) { CloseHandle(mutex); ExitProcess(0); }
    HANDLE stop = CreateEventW(NULL, TRUE, FALSE, stop_name);
    if (!stop) { CloseHandle(mutex); ExitProcess(1); }
    ResetEvent(stop);
    do { EnumWindows(fix_overlay, 0); }
    while (WaitForSingleObject(stop, 1000) == WAIT_TIMEOUT);
    CloseHandle(stop);
    CloseHandle(mutex);
    ExitProcess(0);
}
