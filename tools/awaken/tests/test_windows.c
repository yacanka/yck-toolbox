/* Real Win32 controls, isolated registry, simulated power/timer failures. */
#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>
#include <stdio.h>
#include <stdlib.h>

static BOOL failTimer, failExecution, failPower, failPowerCreate;
static unsigned int dialogs, requests, clears, executionCalls;
static EXECUTION_STATE lastExecution;
static int WINAPI TestMessageBoxW(HWND hwnd, LPCWSTR text, LPCWSTR title, UINT type);
static UINT_PTR WINAPI TestSetTimer(HWND hwnd, UINT_PTR id, UINT timeout, TIMERPROC callback);
static EXECUTION_STATE WINAPI TestExecutionState(EXECUTION_STATE flags);
static FARPROC WINAPI TestGetProcAddress(HMODULE module, LPCSTR name);

#define REGISTRY_SETTINGS_PATH L"Software\\AwakenRegressionTests\\Settings"
#define REGISTRY_RUN_PATH L"Software\\AwakenRegressionTests\\Run"
#define MessageBoxW TestMessageBoxW
#define SetTimer TestSetTimer
#define SetThreadExecutionState TestExecutionState
#define GetProcAddress TestGetProcAddress
#include "../awaken.c"
#undef MessageBoxW
#undef SetTimer
#undef SetThreadExecutionState
#undef GetProcAddress

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr, "Failed at line %d: %s\n", __LINE__, #condition); exit(1); \
} } while (0)

static int WINAPI TestMessageBoxW(HWND hwnd, LPCWSTR text, LPCWSTR title, UINT type) {
    (void)hwnd; (void)text; (void)title; (void)type;
    ++dialogs;
    return IDOK;
}
static UINT_PTR WINAPI TestSetTimer(HWND hwnd, UINT_PTR id, UINT timeout, TIMERPROC callback) {
    (void)hwnd; (void)timeout; (void)callback;
    return failTimer ? 0 : id;
}
static EXECUTION_STATE WINAPI TestExecutionState(EXECUTION_STATE flags) {
    ++executionCalls;
    lastExecution = flags;
    return failExecution ? 0 : ES_CONTINUOUS;
}
static HANDLE WINAPI TestPowerCreate(AppPowerReasonContext *context) {
    CHECK(context->Version == 0);
    if (failPowerCreate) return INVALID_HANDLE_VALUE;
    return CreateEventW(NULL, TRUE, FALSE, NULL);
}
static BOOL WINAPI TestPowerSet(HANDLE handle, int type) {
    CHECK(handle != NULL && type == 0);
    if (failPower) return FALSE;
    ++requests;
    return TRUE;
}
static BOOL WINAPI TestPowerClear(HANDLE handle, int type) {
    CHECK(handle != NULL && type == 0);
    ++clears;
    return TRUE;
}
static FARPROC WINAPI TestGetProcAddress(HMODULE module, LPCSTR name) {
    FARPROC address;
    if (strcmp(name, "PowerCreateRequest") == 0) {
        AppPowerCreateRequestFunction function = TestPowerCreate;
        memcpy(&address, &function, sizeof(address));
        return address;
    }
    if (strcmp(name, "PowerSetRequest") == 0) {
        AppPowerSetRequestFunction function = TestPowerSet;
        memcpy(&address, &function, sizeof(address));
        return address;
    }
    if (strcmp(name, "PowerClearRequest") == 0) {
        AppPowerClearRequestFunction function = TestPowerClear;
        memcpy(&address, &function, sizeof(address));
        return address;
    }
    return GetProcAddress(module, name);
}

static void SelectOptions(BOOL sleep, BOOL display, BOOL saver) {
    Button_SetCheck(g_app.checkSystemSleep, sleep ? BST_CHECKED : BST_UNCHECKED);
    Button_SetCheck(g_app.checkDisplayOff, display ? BST_CHECKED : BST_UNCHECKED);
    Button_SetCheck(g_app.checkScreensaver, saver ? BST_CHECKED : BST_UNCHECKED);
}

int main(void) {
    WNDCLASSW cls = {0};
    INITCOMMONCONTROLSEX controls = {sizeof(controls), ICC_STANDARD_CLASSES};
    HWND hwnd;
    unsigned int before;
    WCHAR text[128];
    HKEY key;
    DWORD invalid = 99;
    CHECK(InitCommonControlsEx(&controls));
    g_app.dpi = 144;
    CHECK(Scale(100) == 150);
    cls.lpfnWndProc = WindowProc;
    cls.hInstance = GetModuleHandleW(NULL);
    cls.lpszClassName = L"AwakenTestWindow";
    CHECK(RegisterClassW(&cls));
    hwnd = CreateWindowW(cls.lpszClassName, L"Test", WS_OVERLAPPEDWINDOW,
        0, 0, 1000, 1000, NULL, NULL, cls.hInstance, NULL);
    CHECK(hwnd != NULL && !g_app.interfaceFailed);
    CHECK(SetStartupEnabled(FALSE));
    CHECK(!IsStartupEnabled());
    CHECK(SetStartupEnabled(TRUE));
    CHECK(IsStartupEnabled());
    CHECK(SetStartupEnabled(FALSE));
    CHECK(!IsStartupEnabled());

    SelectOptions(FALSE, FALSE, FALSE);
    before = dialogs;
    StartProtection(hwnd);
    CHECK(!g_app.active && dialogs == before + 1);
    SelectOptions(TRUE, TRUE, TRUE);
    failPowerCreate = TRUE;
    StartProtection(hwnd);
    CHECK(!g_app.active && g_app.displayPowerRequestHandle == NULL);
    failPowerCreate = FALSE;
    failPower = TRUE;
    StartProtection(hwnd);
    CHECK(!g_app.active && !g_app.executionStateApplied);
    CHECK(g_app.displayPowerRequestHandle == NULL);
    failPower = FALSE;
    failExecution = TRUE;
    StartProtection(hwnd);
    CHECK(!g_app.active && requests == clears);
    failExecution = FALSE;
    failTimer = TRUE;
    StartProtection(hwnd);
    CHECK(!g_app.active && !g_app.executionStateApplied);
    CHECK(lastExecution == ES_CONTINUOUS && requests == clears);
    failTimer = FALSE;

    ComboBox_SetCurSel(g_app.comboDuration, 1);
    StartProtection(hwnd);
    CHECK(g_app.active && g_app.endsAt - g_app.startedAt == 900000);
    CHECK(lastExecution == (ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED));
    CHECK(!IsWindowEnabled(g_app.buttonStart) && IsWindowEnabled(g_app.buttonStop));
    before = requests;
    StartProtection(hwnd);
    CHECK(requests == before);
    failExecution = TRUE;
    CHECK(!StopProtection(hwnd));
    CHECK(g_app.active && g_app.executionStateApplied);
    CHECK(IsWindowEnabled(g_app.buttonStop));
    failExecution = FALSE;
    CHECK(StopProtection(hwnd));
    StartProtection(hwnd);
    before = dialogs;
    g_app.endsAt = GetTickCount64();
    SendMessageW(hwnd, WM_TIMER, ID_TIMER_MAIN, 0);
    CHECK(!g_app.active && requests == clears && dialogs == before);
    CHECK(IsWindowEnabled(g_app.buttonStart) && !IsWindowEnabled(g_app.buttonStop));

    SelectOptions(FALSE, FALSE, TRUE);
    ComboBox_SetCurSel(g_app.comboDuration, 0);
    before = executionCalls;
    StartProtection(hwnd);
    CHECK(g_app.active && g_app.endsAt == 0 && executionCalls == before);
    StopProtection(hwnd);
    CHECK(requests == clears);
    StopProtection(hwnd);
    CHECK(requests == clears);
    FormatRemainingTime(3600001, text, ARRAYSIZE(text));
    CHECK(wcscmp(text, L"Remaining time: 01:00:01") == 0);

    SelectOptions(TRUE, FALSE, FALSE);
    ComboBox_SetCurSel(g_app.comboDuration, 6);
    SaveSettings();
    SelectOptions(FALSE, TRUE, TRUE);
    ComboBox_SetCurSel(g_app.comboDuration, 0);
    LoadSettings();
    CHECK(Button_GetCheck(g_app.checkSystemSleep) == BST_CHECKED);
    CHECK(Button_GetCheck(g_app.checkDisplayOff) == BST_UNCHECKED);
    CHECK(Button_GetCheck(g_app.checkScreensaver) == BST_UNCHECKED);
    CHECK(ComboBox_GetCurSel(g_app.comboDuration) == 6);
    CHECK(RegOpenKeyExW(HKEY_CURRENT_USER, REGISTRY_SETTINGS_PATH, 0, KEY_SET_VALUE, &key) == ERROR_SUCCESS);
    CHECK(WriteRegistryDword(key, L"DurationIndex", invalid));
    RegCloseKey(key);
    LoadSettings();
    CHECK(ComboBox_GetCurSel(g_app.comboDuration) == 0);

    SelectOptions(TRUE, TRUE, TRUE);
    StartProtection(hwnd);
    CHECK(g_app.active);
    SendMessageW(hwnd, WM_POWERBROADCAST, PBT_APMSUSPEND, 0);
    CHECK(!g_app.active && requests == clears);
    StartProtection(hwnd);
    CHECK(g_app.active);
    DestroyWindow(hwnd);
    CHECK(requests == clears && lastExecution == ES_CONTINUOUS);
    CHECK(RegDeleteKeyW(HKEY_CURRENT_USER, REGISTRY_SETTINGS_PATH) == ERROR_SUCCESS);
    CHECK(RegDeleteKeyW(HKEY_CURRENT_USER, REGISTRY_RUN_PATH) == ERROR_SUCCESS);
    CHECK(RegDeleteKeyW(HKEY_CURRENT_USER, L"Software\\AwakenRegressionTests") == ERROR_SUCCESS);
    puts("Awaken Windows lifecycle tests passed");
    return 0;
}
