#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include <commctrl.h>
#include <windowsx.h>
#include <strsafe.h>
#include <stdint.h>
#include <wchar.h>

#include "resource.h"

#ifdef _MSC_VER
#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(linker, \
    "\"/manifestdependency:type='win32' name='Microsoft.Windows.Common-Controls' " \
    "version='6.0.0.0' processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'\"")
#endif

#define APP_CLASS_NAME             L"IAmAwakeWindowClass"
#define APP_TITLE                  L"I am awake"
#define REGISTRY_SETTINGS_PATH     L"Software\\IAmAwake"
#define REGISTRY_RUN_PATH          L"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
#define REGISTRY_RUN_VALUE         L"IAmAwake"

#define ID_CHECK_SYSTEM_SLEEP      1001
#define ID_CHECK_DISPLAY_OFF       1002
#define ID_CHECK_SCREENSAVER       1003
#define ID_COMBO_DURATION          1004
#define ID_CHECK_STARTUP           1005
#define ID_BUTTON_START            1006
#define ID_BUTTON_STOP             1007
#define ID_STATUS_TEXT             1008
#define ID_REMAINING_TEXT          1009
#define ID_TIMER_MAIN              2001

#define WINDOW_WIDTH               620
#define WINDOW_HEIGHT              570

static const COLORREF APP_COLOR_BACKGROUND = RGB(246, 248, 251);
static const COLORREF COLOR_TEXT = RGB(31, 41, 55);
static const COLORREF COLOR_MUTED = RGB(91, 101, 116);
static const COLORREF COLOR_ACTIVE = RGB(20, 122, 72);
static const COLORREF COLOR_INACTIVE = RGB(165, 48, 48);

typedef struct AppState {
    HWND hwnd;
    HWND checkSystemSleep;
    HWND checkDisplayOff;
    HWND checkScreensaver;
    HWND comboDuration;
    HWND checkStartup;
    HWND buttonStart;
    HWND buttonStop;
    HWND statusText;
    HWND remainingText;

    HFONT fontNormal;
    HFONT fontSmall;
    HFONT fontTitle;
    HFONT fontButton;
    HBRUSH backgroundBrush;

    BOOL active;
    BOOL executionStateApplied;
    HANDLE displayPowerRequestHandle;
    BOOL displayPowerRequestApplied;
    BOOL displayPowerRequestFailed;

    ULONGLONG startedAt;
    ULONGLONG endsAt;
} AppState;

static AppState g_app;

/*
 * Some older MinGW-w64 headers do not provide the PowerCreateRequest and
 * PowerSetRequest types, so ABI-compatible application-local definitions
 * are used here. Official POWER_REQUEST_TYPE value:
 * PowerRequestDisplayRequired = 0.
 */
typedef struct AppPowerReasonContext {
    ULONG Version;
    DWORD Flags;
    union {
        struct {
            HMODULE LocalizedReasonModule;
            ULONG LocalizedReasonId;
            ULONG ReasonStringCount;
            LPWSTR *ReasonStrings;
        } Detailed;
        LPWSTR SimpleReasonString;
    } Reason;
} AppPowerReasonContext;

typedef HANDLE (WINAPI *AppPowerCreateRequestFunction)(AppPowerReasonContext *context);
typedef BOOL (WINAPI *AppPowerSetRequestFunction)(HANDLE requestHandle, int requestType);
typedef BOOL (WINAPI *AppPowerClearRequestFunction)(HANDLE requestHandle, int requestType);

#define APP_POWER_REQUEST_CONTEXT_VERSION       0UL
#define APP_POWER_REQUEST_CONTEXT_SIMPLE_STRING 0x00000001UL
static const int PowerRequestDisplayRequiredValue = 0;

static HICON LoadApplicationIcon(HINSTANCE instance, int width, int height) {
    HICON icon = (HICON)LoadImageW(
        instance,
        MAKEINTRESOURCEW(IDI_APP_ICON),
        IMAGE_ICON,
        width,
        height,
        LR_DEFAULTCOLOR | LR_SHARED
    );

    if (icon == NULL) {
        icon = LoadIconW(NULL, IDI_APPLICATION);
    }

    return icon;
}

static LRESULT CALLBACK WindowProc(HWND hwnd, UINT message, WPARAM wParam, LPARAM lParam);
static void StartProtection(HWND hwnd);
static void StopProtection(HWND hwnd);
static void UpdateStatusText(void);
static void SaveSettings(void);

/*
 * Older MinGW-w64 SDK/import-library versions may declare SetProcessDPIAware
 * without exporting the symbol from their user32 import library. Loading the
 * function at runtime keeps the program compatible with old and new toolchains.
 */
static void EnableDpiAwarenessIfSupported(void) {
    typedef BOOL (WINAPI *SetProcessDPIAwareFunction)(void);
    HMODULE user32Module = GetModuleHandleW(L"user32.dll");
    FARPROC procedureAddress;

    if (user32Module == NULL) {
        return;
    }

    procedureAddress = GetProcAddress(user32Module, "SetProcessDPIAware");
    if (procedureAddress != NULL) {
        SetProcessDPIAwareFunction setProcessDPIAwareFunction;
        setProcessDPIAwareFunction = (SetProcessDPIAwareFunction)procedureAddress;
        (void)setProcessDPIAwareFunction();
    }
}

static BOOL ApplyPowerRequestDisplayRequired(void) {
    HMODULE kernel32Module;
    AppPowerCreateRequestFunction powerCreateRequest;
    AppPowerSetRequestFunction powerSetRequest;
    AppPowerReasonContext reasonContext;
    HANDLE requestHandle;

    if (g_app.displayPowerRequestApplied) {
        return TRUE;
    }

    kernel32Module = GetModuleHandleW(L"kernel32.dll");
    if (kernel32Module == NULL) {
        return FALSE;
    }

    powerCreateRequest = (AppPowerCreateRequestFunction)(void *)
        GetProcAddress(kernel32Module, "PowerCreateRequest");
    powerSetRequest = (AppPowerSetRequestFunction)(void *)
        GetProcAddress(kernel32Module, "PowerSetRequest");

    if (powerCreateRequest == NULL || powerSetRequest == NULL) {
        return FALSE;
    }

    ZeroMemory(&reasonContext, sizeof(reasonContext));
    reasonContext.Version = APP_POWER_REQUEST_CONTEXT_VERSION;
    reasonContext.Flags = APP_POWER_REQUEST_CONTEXT_SIMPLE_STRING;
    reasonContext.Reason.SimpleReasonString =
        L"I am awake is preventing the screen saver and automatic display timeout.";

    requestHandle = powerCreateRequest(&reasonContext);
    if (requestHandle == NULL || requestHandle == INVALID_HANDLE_VALUE) {
        return FALSE;
    }

    /* Core call: PowerSetRequest(..., PowerRequestDisplayRequired). */
    if (!powerSetRequest(requestHandle, PowerRequestDisplayRequiredValue)) {
        CloseHandle(requestHandle);
        return FALSE;
    }

    g_app.displayPowerRequestHandle = requestHandle;
    g_app.displayPowerRequestApplied = TRUE;
    return TRUE;
}

static void ClearPowerRequestDisplayRequired(void) {
    HMODULE kernel32Module;
    AppPowerClearRequestFunction powerClearRequest;

    if (g_app.displayPowerRequestHandle == NULL) {
        g_app.displayPowerRequestApplied = FALSE;
        return;
    }

    kernel32Module = GetModuleHandleW(L"kernel32.dll");
    if (kernel32Module != NULL) {
        powerClearRequest = (AppPowerClearRequestFunction)(void *)
            GetProcAddress(kernel32Module, "PowerClearRequest");

        if (powerClearRequest != NULL && g_app.displayPowerRequestApplied) {
            (void)powerClearRequest(
                g_app.displayPowerRequestHandle,
                PowerRequestDisplayRequiredValue
            );
        }
    }

    CloseHandle(g_app.displayPowerRequestHandle);
    g_app.displayPowerRequestHandle = NULL;
    g_app.displayPowerRequestApplied = FALSE;
}

static HWND CreateControl(
    DWORD exStyle,
    LPCWSTR className,
    LPCWSTR text,
    DWORD style,
    int x,
    int y,
    int width,
    int height,
    HWND parent,
    int controlId,
    HFONT font
) {
    HWND control = CreateWindowExW(
        exStyle,
        className,
        text,
        style,
        x,
        y,
        width,
        height,
        parent,
        (HMENU)(INT_PTR)controlId,
        GetModuleHandleW(NULL),
        NULL
    );

    if (control != NULL && font != NULL) {
        SendMessageW(control, WM_SETFONT, (WPARAM)font, TRUE);
    }

    return control;
}

static BOOL ReadRegistryDword(LPCWSTR valueName, DWORD *value) {
    HKEY key = NULL;
    DWORD type = 0;
    DWORD size = sizeof(*value);
    LONG result;

    if (value == NULL) {
        return FALSE;
    }

    result = RegOpenKeyExW(HKEY_CURRENT_USER, REGISTRY_SETTINGS_PATH, 0, KEY_QUERY_VALUE, &key);
    if (result != ERROR_SUCCESS) {
        return FALSE;
    }

    result = RegQueryValueExW(key, valueName, NULL, &type, (LPBYTE)value, &size);
    RegCloseKey(key);

    return result == ERROR_SUCCESS && type == REG_DWORD && size == sizeof(*value);
}

static void WriteRegistryDword(HKEY key, LPCWSTR valueName, DWORD value) {
    RegSetValueExW(key, valueName, 0, REG_DWORD, (const BYTE *)&value, sizeof(value));
}

static BOOL IsStartupEnabled(void) {
    HKEY key = NULL;
    LONG result;
    DWORD type = 0;
    DWORD size = 0;

    result = RegOpenKeyExW(HKEY_CURRENT_USER, REGISTRY_RUN_PATH, 0, KEY_QUERY_VALUE, &key);
    if (result != ERROR_SUCCESS) {
        return FALSE;
    }

    result = RegQueryValueExW(key, REGISTRY_RUN_VALUE, NULL, &type, NULL, &size);
    RegCloseKey(key);

    return result == ERROR_SUCCESS && (type == REG_SZ || type == REG_EXPAND_SZ) && size > sizeof(WCHAR);
}

static BOOL SetStartupEnabled(BOOL enabled) {
    HKEY key = NULL;
    LONG result;

    result = RegCreateKeyExW(
        HKEY_CURRENT_USER,
        REGISTRY_RUN_PATH,
        0,
        NULL,
        REG_OPTION_NON_VOLATILE,
        KEY_SET_VALUE,
        NULL,
        &key,
        NULL
    );

    if (result != ERROR_SUCCESS) {
        return FALSE;
    }

    if (enabled) {
        WCHAR executablePath[MAX_PATH];
        WCHAR commandLine[(MAX_PATH * 2) + 8];
        DWORD pathLength = GetModuleFileNameW(NULL, executablePath, MAX_PATH);

        if (pathLength == 0 || pathLength >= MAX_PATH) {
            RegCloseKey(key);
            return FALSE;
        }

        if (FAILED(StringCchPrintfW(commandLine, ARRAYSIZE(commandLine), L"\"%s\" --activate", executablePath))) {
            RegCloseKey(key);
            return FALSE;
        }

        result = RegSetValueExW(
            key,
            REGISTRY_RUN_VALUE,
            0,
            REG_SZ,
            (const BYTE *)commandLine,
            (DWORD)((wcslen(commandLine) + 1) * sizeof(WCHAR))
        );
    } else {
        result = RegDeleteValueW(key, REGISTRY_RUN_VALUE);
        if (result == ERROR_FILE_NOT_FOUND) {
            result = ERROR_SUCCESS;
        }
    }

    RegCloseKey(key);
    return result == ERROR_SUCCESS;
}

static void LoadSettings(void) {
    DWORD value;
    int durationIndex = 0;

    Button_SetCheck(g_app.checkSystemSleep, BST_CHECKED);
    Button_SetCheck(g_app.checkDisplayOff, BST_CHECKED);
    Button_SetCheck(g_app.checkScreensaver, BST_CHECKED);

    if (ReadRegistryDword(L"PreventSystemSleep", &value)) {
        Button_SetCheck(g_app.checkSystemSleep, value ? BST_CHECKED : BST_UNCHECKED);
    }
    if (ReadRegistryDword(L"PreventDisplayOff", &value)) {
        Button_SetCheck(g_app.checkDisplayOff, value ? BST_CHECKED : BST_UNCHECKED);
    }
    if (ReadRegistryDword(L"PreventScreensaver", &value)) {
        Button_SetCheck(g_app.checkScreensaver, value ? BST_CHECKED : BST_UNCHECKED);
    }
    if (ReadRegistryDword(L"DurationIndex", &value) && value <= 6) {
        durationIndex = (int)value;
    }

    ComboBox_SetCurSel(g_app.comboDuration, durationIndex);
    Button_SetCheck(g_app.checkStartup, IsStartupEnabled() ? BST_CHECKED : BST_UNCHECKED);
}

static void SaveSettings(void) {
    HKEY key = NULL;
    LONG result = RegCreateKeyExW(
        HKEY_CURRENT_USER,
        REGISTRY_SETTINGS_PATH,
        0,
        NULL,
        REG_OPTION_NON_VOLATILE,
        KEY_SET_VALUE,
        NULL,
        &key,
        NULL
    );

    if (result != ERROR_SUCCESS) {
        return;
    }

    WriteRegistryDword(
        key,
        L"PreventSystemSleep",
        Button_GetCheck(g_app.checkSystemSleep) == BST_CHECKED
    );
    WriteRegistryDword(
        key,
        L"PreventDisplayOff",
        Button_GetCheck(g_app.checkDisplayOff) == BST_CHECKED
    );
    WriteRegistryDword(
        key,
        L"PreventScreensaver",
        Button_GetCheck(g_app.checkScreensaver) == BST_CHECKED
    );
    WriteRegistryDword(
        key,
        L"DurationIndex",
        (DWORD)ComboBox_GetCurSel(g_app.comboDuration)
    );

    RegCloseKey(key);
}

static int DurationMinutesFromSelection(int selection) {
    switch (selection) {
        case 1: return 15;
        case 2: return 30;
        case 3: return 60;
        case 4: return 120;
        case 5: return 240;
        case 6: return 480;
        default: return 0;
    }
}

static void SetConfigurationControlsEnabled(BOOL enabled) {
    EnableWindow(g_app.checkSystemSleep, enabled);
    EnableWindow(g_app.checkDisplayOff, enabled);
    EnableWindow(g_app.checkScreensaver, enabled);
    EnableWindow(g_app.comboDuration, enabled);
    EnableWindow(g_app.buttonStart, enabled);
    EnableWindow(g_app.buttonStop, !enabled);
}

static void FormatRemainingTime(ULONGLONG milliseconds, WCHAR *buffer, size_t bufferCount) {
    ULONGLONG totalSeconds = (milliseconds + 999ULL) / 1000ULL;
    ULONGLONG hours = totalSeconds / 3600ULL;
    ULONGLONG minutes = (totalSeconds % 3600ULL) / 60ULL;
    ULONGLONG seconds = totalSeconds % 60ULL;

    StringCchPrintfW(
        buffer,
        bufferCount,
        L"Remaining time: %02llu:%02llu:%02llu",
        (unsigned long long)hours,
        (unsigned long long)minutes,
        (unsigned long long)seconds
    );
}

static void UpdateStatusText(void) {
    WCHAR remaining[128];

    if (!g_app.active) {
        SetWindowTextW(g_app.statusText, L"● Inactive — Windows power settings are in effect");
        SetWindowTextW(g_app.remainingText, L"Protection is not active");
        InvalidateRect(g_app.statusText, NULL, TRUE);
        return;
    }

    if (g_app.displayPowerRequestFailed) {
        SetWindowTextW(
            g_app.statusText,
            L"● Active — Sleep protection is running; PowerRequestDisplayRequired could not be applied"
        );
    } else {
        SetWindowTextW(g_app.statusText, L"● Active — This computer is being kept awake");
    }

    if (g_app.endsAt == 0) {
        SetWindowTextW(g_app.remainingText, L"Duration: Unlimited");
    } else {
        ULONGLONG now = GetTickCount64();
        ULONGLONG remainingMs = g_app.endsAt > now ? g_app.endsAt - now : 0;
        FormatRemainingTime(remainingMs, remaining, ARRAYSIZE(remaining));
        SetWindowTextW(g_app.remainingText, remaining);
    }

    InvalidateRect(g_app.statusText, NULL, TRUE);
}

static void StartProtection(HWND hwnd) {
    BOOL preventSystemSleep = Button_GetCheck(g_app.checkSystemSleep) == BST_CHECKED;
    BOOL preventDisplayOff = Button_GetCheck(g_app.checkDisplayOff) == BST_CHECKED;
    BOOL preventScreensaver = Button_GetCheck(g_app.checkScreensaver) == BST_CHECKED;
    EXECUTION_STATE executionFlags = ES_CONTINUOUS;
    int durationMinutes;

    if (g_app.active) {
        return;
    }

    if (!preventSystemSleep && !preventDisplayOff && !preventScreensaver) {
        MessageBoxW(
            hwnd,
            L"Select at least one protection option.",
            APP_TITLE,
            MB_OK | MB_ICONINFORMATION
        );
        return;
    }

    g_app.executionStateApplied = FALSE;
    g_app.displayPowerRequestFailed = FALSE;

    if (preventScreensaver) {
        if (!ApplyPowerRequestDisplayRequired()) {
            g_app.displayPowerRequestFailed = TRUE;
        }
    }

    if (preventSystemSleep) {
        executionFlags |= ES_SYSTEM_REQUIRED;
    }
    if (preventDisplayOff || (preventScreensaver && g_app.displayPowerRequestFailed)) {
        executionFlags |= ES_DISPLAY_REQUIRED;
    }

    if (executionFlags != ES_CONTINUOUS) {
        if (SetThreadExecutionState(executionFlags) == 0) {
            ClearPowerRequestDisplayRequired();
            MessageBoxW(
                hwnd,
                L"The Windows power request could not be applied.",
                APP_TITLE,
                MB_OK | MB_ICONERROR
            );
            return;
        }
        g_app.executionStateApplied = TRUE;
    }

    durationMinutes = DurationMinutesFromSelection(ComboBox_GetCurSel(g_app.comboDuration));
    g_app.startedAt = GetTickCount64();
    g_app.endsAt = durationMinutes > 0
        ? g_app.startedAt + ((ULONGLONG)durationMinutes * 60ULL * 1000ULL)
        : 0;
    g_app.active = TRUE;

    SetConfigurationControlsEnabled(FALSE);
    SetTimer(hwnd, ID_TIMER_MAIN, 1000, NULL);
    SaveSettings();
    UpdateStatusText();
}

static void StopProtection(HWND hwnd) {
    (void)hwnd;

    KillTimer(g_app.hwnd, ID_TIMER_MAIN);

    if (g_app.executionStateApplied) {
        SetThreadExecutionState(ES_CONTINUOUS);
        g_app.executionStateApplied = FALSE;
    }

    ClearPowerRequestDisplayRequired();
    g_app.displayPowerRequestFailed = FALSE;

    g_app.active = FALSE;
    g_app.startedAt = 0;
    g_app.endsAt = 0;

    SetConfigurationControlsEnabled(TRUE);
    UpdateStatusText();
}

static void CreateFonts(void) {
    HDC hdc = GetDC(NULL);
    int dpiY = GetDeviceCaps(hdc, LOGPIXELSY);
    ReleaseDC(NULL, hdc);

    g_app.fontNormal = CreateFontW(
        -MulDiv(10, dpiY, 72), 0, 0, 0, FW_NORMAL,
        FALSE, FALSE, FALSE, DEFAULT_CHARSET,
        OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
        DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI"
    );

    g_app.fontSmall = CreateFontW(
        -MulDiv(9, dpiY, 72), 0, 0, 0, FW_NORMAL,
        FALSE, FALSE, FALSE, DEFAULT_CHARSET,
        OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
        DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI"
    );

    g_app.fontTitle = CreateFontW(
        -MulDiv(22, dpiY, 72), 0, 0, 0, FW_SEMIBOLD,
        FALSE, FALSE, FALSE, DEFAULT_CHARSET,
        OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
        DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI"
    );

    g_app.fontButton = CreateFontW(
        -MulDiv(10, dpiY, 72), 0, 0, 0, FW_SEMIBOLD,
        FALSE, FALSE, FALSE, DEFAULT_CHARSET,
        OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
        DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI"
    );
}

static void CreateInterface(HWND hwnd) {
    HWND title;
    HWND subtitle;
    HWND groupProtection;
    HWND durationLabel;
    HWND groupBehavior;
    HWND note;
    HWND footer;

    CreateFonts();

    title = CreateControl(
        0, L"STATIC", APP_TITLE,
        WS_CHILD | WS_VISIBLE,
        28, 22, 550, 42,
        hwnd, 0, g_app.fontTitle
    );
    (void)title;

    subtitle = CreateControl(
        0, L"STATIC",
        L"Prevent sleep, display timeout, and screen saver activation while the computer is idle.",
        WS_CHILD | WS_VISIBLE,
        30, 66, 550, 42,
        hwnd, 0, g_app.fontNormal
    );
    (void)subtitle;

    groupProtection = CreateControl(
        0, L"BUTTON", L"Protection options",
        WS_CHILD | WS_VISIBLE | BS_GROUPBOX,
        26, 112, 558, 176,
        hwnd, 0, g_app.fontNormal
    );
    (void)groupProtection;

    g_app.checkSystemSleep = CreateControl(
        0, L"BUTTON", L"Prevent the computer from going to sleep automatically",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
        48, 145, 500, 28,
        hwnd, ID_CHECK_SYSTEM_SLEEP, g_app.fontNormal
    );

    g_app.checkDisplayOff = CreateControl(
        0, L"BUTTON", L"Prevent the display from turning off or dimming automatically",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
        48, 183, 500, 28,
        hwnd, ID_CHECK_DISPLAY_OFF, g_app.fontNormal
    );

    g_app.checkScreensaver = CreateControl(
        0, L"BUTTON", L"Prevent the screen saver from starting automatically",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
        48, 221, 500, 28,
        hwnd, ID_CHECK_SCREENSAVER, g_app.fontNormal
    );

    durationLabel = CreateControl(
        0, L"STATIC", L"Protection duration:",
        WS_CHILD | WS_VISIBLE,
        48, 258, 120, 24,
        hwnd, 0, g_app.fontNormal
    );
    (void)durationLabel;

    g_app.comboDuration = CreateControl(
        0, L"COMBOBOX", L"",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST | WS_VSCROLL,
        174, 254, 210, 250,
        hwnd, ID_COMBO_DURATION, g_app.fontNormal
    );

    ComboBox_AddString(g_app.comboDuration, L"Unlimited — until stopped");
    ComboBox_AddString(g_app.comboDuration, L"15 minutes");
    ComboBox_AddString(g_app.comboDuration, L"30 minutes");
    ComboBox_AddString(g_app.comboDuration, L"1 hour");
    ComboBox_AddString(g_app.comboDuration, L"2 hours");
    ComboBox_AddString(g_app.comboDuration, L"4 hours");
    ComboBox_AddString(g_app.comboDuration, L"8 hours");

    groupBehavior = CreateControl(
        0, L"BUTTON", L"Application",
        WS_CHILD | WS_VISIBLE | BS_GROUPBOX,
        26, 302, 558, 74,
        hwnd, 0, g_app.fontNormal
    );
    (void)groupBehavior;

    g_app.checkStartup = CreateControl(
        0, L"BUTTON", L"Start I am awake with Windows and activate protection",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
        48, 330, 500, 28,
        hwnd, ID_CHECK_STARTUP, g_app.fontNormal
    );

    g_app.statusText = CreateControl(
        0, L"STATIC", L"",
        WS_CHILD | WS_VISIBLE,
        30, 398, 555, 28,
        hwnd, ID_STATUS_TEXT, g_app.fontButton
    );

    g_app.remainingText = CreateControl(
        0, L"STATIC", L"",
        WS_CHILD | WS_VISIBLE,
        30, 426, 555, 24,
        hwnd, ID_REMAINING_TEXT, g_app.fontNormal
    );

    g_app.buttonStart = CreateControl(
        0, L"BUTTON", L"Activate",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_DEFPUSHBUTTON,
        30, 462, 266, 42,
        hwnd, ID_BUTTON_START, g_app.fontButton
    );

    g_app.buttonStop = CreateControl(
        0, L"BUTTON", L"Stop",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
        312, 462, 266, 42,
        hwnd, ID_BUTTON_STOP, g_app.fontButton
    );

    note = CreateControl(
        0, L"STATIC",
        L"Note: Manual sleep, shutdown, screen lock, and laptop lid actions are not blocked.",
        WS_CHILD | WS_VISIBLE,
        30, 516, 555, 34,
        hwnd, 0, g_app.fontSmall
    );
    (void)note;

    footer = CreateControl(
        0, L"STATIC", L"Settings are stored in your user account; administrator privileges are not required.",
        WS_CHILD | WS_VISIBLE,
        30, 548, 555, 22,
        hwnd, 0, g_app.fontSmall
    );
    (void)footer;

    LoadSettings();
    SetConfigurationControlsEnabled(TRUE);
    UpdateStatusText();
}

static LRESULT HandleControlColor(HDC hdc, HWND control) {
    SetBkMode(hdc, TRANSPARENT);

    if (control == g_app.statusText) {
        SetTextColor(hdc, g_app.active ? COLOR_ACTIVE : COLOR_INACTIVE);
    } else if (control == g_app.remainingText) {
        SetTextColor(hdc, COLOR_TEXT);
    } else {
        SetTextColor(hdc, COLOR_MUTED);
    }

    return (LRESULT)g_app.backgroundBrush;
}

static LRESULT CALLBACK WindowProc(HWND hwnd, UINT message, WPARAM wParam, LPARAM lParam) {
    switch (message) {
        case WM_CREATE:
            g_app.hwnd = hwnd;
            g_app.backgroundBrush = CreateSolidBrush(APP_COLOR_BACKGROUND);
            CreateInterface(hwnd);
            return 0;

        case WM_COMMAND: {
            int controlId = LOWORD(wParam);
            int notification = HIWORD(wParam);

            if (controlId == ID_BUTTON_START && notification == BN_CLICKED) {
                StartProtection(hwnd);
                return 0;
            }

            if (controlId == ID_BUTTON_STOP && notification == BN_CLICKED) {
                StopProtection(hwnd);
                return 0;
            }

            if (controlId == ID_CHECK_STARTUP && notification == BN_CLICKED) {
                BOOL requested = Button_GetCheck(g_app.checkStartup) == BST_CHECKED;
                if (!SetStartupEnabled(requested)) {
                    Button_SetCheck(g_app.checkStartup, requested ? BST_UNCHECKED : BST_CHECKED);
                    MessageBoxW(
                        hwnd,
                        L"The Windows startup setting could not be changed.",
                        APP_TITLE,
                        MB_OK | MB_ICONERROR
                    );
                }
                return 0;
            }

            if ((controlId == ID_CHECK_SYSTEM_SLEEP ||
                 controlId == ID_CHECK_DISPLAY_OFF ||
                 controlId == ID_CHECK_SCREENSAVER) &&
                notification == BN_CLICKED) {
                SaveSettings();
                return 0;
            }

            if (controlId == ID_COMBO_DURATION && notification == CBN_SELCHANGE) {
                SaveSettings();
                return 0;
            }
            break;
        }

        case WM_TIMER:
            if (wParam == ID_TIMER_MAIN && g_app.active) {
                if (g_app.endsAt != 0 && GetTickCount64() >= g_app.endsAt) {
                    StopProtection(hwnd);
                    MessageBoxW(
                        hwnd,
                        L"The selected protection duration has ended.",
                        APP_TITLE,
                        MB_OK | MB_ICONINFORMATION
                    );
                } else {
                    UpdateStatusText();
                }
                return 0;
            }
            break;

        case WM_SYSCOMMAND:
            if (g_app.active) {
                UINT command = (UINT)(wParam & 0xFFF0U);
                BOOL preventDisplayOff = Button_GetCheck(g_app.checkDisplayOff) == BST_CHECKED;
                BOOL preventScreensaver = Button_GetCheck(g_app.checkScreensaver) == BST_CHECKED;

                if (command == SC_SCREENSAVE && preventScreensaver) {
                    return 0;
                }
                if (command == SC_MONITORPOWER && preventDisplayOff) {
                    return 0;
                }
            }
            break;

        case WM_CTLCOLORSTATIC:
            return HandleControlColor((HDC)wParam, (HWND)lParam);

        case WM_CTLCOLORBTN:
            SetBkMode((HDC)wParam, TRANSPARENT);
            SetTextColor((HDC)wParam, COLOR_TEXT);
            return (LRESULT)g_app.backgroundBrush;

        case WM_ERASEBKGND: {
            RECT rect;
            GetClientRect(hwnd, &rect);
            FillRect((HDC)wParam, &rect, g_app.backgroundBrush);
            return 1;
        }

        case WM_CLOSE:
            SaveSettings();
            StopProtection(hwnd);
            DestroyWindow(hwnd);
            return 0;

        case WM_ENDSESSION:
            if (wParam) {
                if (g_app.executionStateApplied) {
                    SetThreadExecutionState(ES_CONTINUOUS);
                    g_app.executionStateApplied = FALSE;
                }
                ClearPowerRequestDisplayRequired();
            }
            return 0;

        case WM_DESTROY:
            if (g_app.executionStateApplied) {
                SetThreadExecutionState(ES_CONTINUOUS);
                g_app.executionStateApplied = FALSE;
            }
            ClearPowerRequestDisplayRequired();
            if (g_app.fontNormal) DeleteObject(g_app.fontNormal);
            if (g_app.fontSmall) DeleteObject(g_app.fontSmall);
            if (g_app.fontTitle) DeleteObject(g_app.fontTitle);
            if (g_app.fontButton) DeleteObject(g_app.fontButton);
            if (g_app.backgroundBrush) DeleteObject(g_app.backgroundBrush);
            PostQuitMessage(0);
            return 0;
    }

    return DefWindowProcW(hwnd, message, wParam, lParam);
}

/*
 * Some older MinGW-w64 windows.h versions map WinMain to wWinMain when
 * UNICODE is defined. The program still uses the Unicode Win32 API, but the
 * real entry point remains ANSI-signature WinMain for -mwindows compatibility.
 */
#ifdef WinMain
#undef WinMain
#endif

int WINAPI WinMain(HINSTANCE instance, HINSTANCE previousInstance, LPSTR commandLine, int showCommand) {
    WNDCLASSEXW windowClass;
    HWND hwnd;
    MSG message;
    INITCOMMONCONTROLSEX commonControls;
    RECT windowRect = {0, 0, WINDOW_WIDTH, WINDOW_HEIGHT};
    BOOL activateOnLaunch;
    BOOL getMessageResult;
    HICON largeIcon;
    HICON smallIcon;

    (void)previousInstance;
    (void)commandLine;
    activateOnLaunch = wcsstr(GetCommandLineW(), L"--activate") != NULL;

    ZeroMemory(&g_app, sizeof(g_app));
    EnableDpiAwarenessIfSupported();

    commonControls.dwSize = sizeof(commonControls);
    commonControls.dwICC = ICC_STANDARD_CLASSES;
    InitCommonControlsEx(&commonControls);

    largeIcon = LoadApplicationIcon(
        instance,
        GetSystemMetrics(SM_CXICON),
        GetSystemMetrics(SM_CYICON)
    );
    smallIcon = LoadApplicationIcon(
        instance,
        GetSystemMetrics(SM_CXSMICON),
        GetSystemMetrics(SM_CYSMICON)
    );

    ZeroMemory(&windowClass, sizeof(windowClass));
    windowClass.cbSize = sizeof(windowClass);
    windowClass.style = CS_HREDRAW | CS_VREDRAW;
    windowClass.lpfnWndProc = WindowProc;
    windowClass.hInstance = instance;
    windowClass.hIcon = largeIcon;
    windowClass.hCursor = LoadCursorW(NULL, IDC_ARROW);
    windowClass.hbrBackground = NULL;
    windowClass.lpszClassName = APP_CLASS_NAME;
    windowClass.hIconSm = smallIcon;

    if (!RegisterClassExW(&windowClass)) {
        MessageBoxW(NULL, L"The application window class could not be registered.", APP_TITLE, MB_OK | MB_ICONERROR);
        return 1;
    }

    AdjustWindowRectEx(&windowRect, WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX, FALSE, 0);

    hwnd = CreateWindowExW(
        0,
        APP_CLASS_NAME,
        APP_TITLE,
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        windowRect.right - windowRect.left,
        windowRect.bottom - windowRect.top,
        NULL,
        NULL,
        instance,
        NULL
    );

    if (hwnd == NULL) {
        MessageBoxW(NULL, L"The application window could not be created.", APP_TITLE, MB_OK | MB_ICONERROR);
        return 1;
    }

    SendMessageW(hwnd, WM_SETICON, ICON_BIG, (LPARAM)largeIcon);
    SendMessageW(hwnd, WM_SETICON, ICON_SMALL, (LPARAM)smallIcon);

    ShowWindow(hwnd, showCommand);
    UpdateWindow(hwnd);

    if (activateOnLaunch) {
        StartProtection(hwnd);
    }

    while ((getMessageResult = (BOOL)GetMessageW(&message, NULL, 0, 0)) > 0) {
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }

    return getMessageResult == -1 ? 1 : (int)message.wParam;
}
