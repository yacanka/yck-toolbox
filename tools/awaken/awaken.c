/*
 * Awaken 1.0.0 - single-file Windows desktop utility.
 * This file contains the application, resources, tests and build instructions.
 * No project files, resource headers, external manifests or libraries beyond
 * the Windows SDK are required. Windows 10/11 are the deployment targets.
 *
 * MSVC (Visual Studio Developer Command Prompt, from this directory):
 *   rc /nologo /d AWAKEN_RESOURCES /fo awaken.res awaken.c
 *   cl /nologo /std:c11 /W4 /WX /utf-8 /MT awaken.c awaken.res /Fe:awaken.exe /link /SUBSYSTEM:WINDOWS /MANIFEST:NO /DYNAMICBASE /NXCOMPAT
 *
 * MinGW-w64 (native or cross-build, from this directory):
 *   x86_64-w64-mingw32-windres -DAWAKEN_RESOURCES -J rc -O coff -i awaken.c -o awaken.res
 *   x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -mwindows -static awaken.c awaken.res -o awaken.exe -lcomctl32 -ladvapi32 -lshell32 -lgdi32 -luser32 -Wl,--dynamicbase,--nxcompat
 * Use i686-w64-mingw32-* for x86. Only awaken.exe is needed at runtime.
 * Dev-C++: compile this file as C (no AWAKEN_* test/resource defines).
 * Set the project icon in Dev-C++ and rebuild its resources. Awaken loads the
 * first usable embedded icon group for the title bar, taskbar and Alt+Tab.
 * Named and numeric resource IDs are supported; no resource.h is needed.
 * Without an embedded icon, Awaken uses a Windows fallback icon.
 * Linker options: -mwindows -static -lcomctl32 -ladvapi32 -lshell32 -lgdi32 -luser32
 * Resource and object files are build outputs, not additional source files.
 * Building only awaken.c also works with classic controls; include resources
 * for the version metadata and themed controls. Standard-control initialization
 * falls back when the v6 activation context is unavailable.
 *
 * Portable regression tests (macOS/Linux/Windows):
 *   cc -std=c11 -Wall -Wextra -Werror -DAWAKEN_LOGIC_TEST awaken.c -o awaken_logic_tests
 *   ./awaken_logic_tests
 * Windows lifecycle tests (Developer Command Prompt):
 *   cl /nologo /std:c11 /W4 /WX /utf-8 /MT /DAWAKEN_WINDOWS_TEST awaken.c /Fe:awaken_windows_tests.exe
 *   awaken_windows_tests.exe
 * For MSVC portable tests use /DAWAKEN_LOGIC_TEST in the same command.
 * Tests use real controls with simulated power/timer failures and isolated keys
 * under HKCU\Software\AwakenRegressionTests (removed on success).
 * No test code or test Registry overrides are included in the normal executable.
 *
 * Usage: select protection, select a duration, then Activate. Stop, expiry or
 * closing the window releases requests. Minimize keeps protection active.
 * Tab/Shift+Tab navigate; Space toggles; Alt+A activates; Alt+T stops;
 * Alt+D toggles display protection; Alt+R toggles shutdown protection;
 * Alt+U selects duration.
 * Only a separate exact --activate argument auto-starts with saved options.
 * A second launch shows the existing instance without restarting its timer.
 *
 * Prevent screen saver also keeps the display on. Select sleep protection too
 * if the computer must stay awake. Manual sleep, locking, lid actions and policy
 * remain effective. Suspend ends the session; activate again after resume.
 * Windows may override power requests, especially on battery/Modern Standby.
 * This application does not simulate input or alter global power settings.
 * https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-powersetrequest
 * https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate
 *
 * Shutdown protection is opt-in and blocks normal shutdown, restart, sign-out
 * and application-restart requests while active, including when minimized.
 * Windows cannot distinguish shutdown from restart here. Forced termination,
 * critical shutdown, "Shut down anyway", crashes and power loss can override it.
 * No shutdown commands are polled or aborted; no privileges or policies change.
 * Stop, expiry, suspend and exit release the block. A canceled shutdown keeps it.
 * https://learn.microsoft.com/en-us/windows/win32/shutdown/wm-queryendsession
 *
 * Settings: HKCU\Software\Awaken. Auto-start: the Awaken value in
 * HKCU\Software\Microsoft\Windows\CurrentVersion\Run. No admin rights needed.
 * Naming upgrade: settings from the previous product name are not migrated.
 * Disable auto-start in the previous version before replacing it; re-enable
 * from Awaken if desired. Disable auto-start before moving/removing the exe.
 * Uninstall: disable auto-start, close, remove exe; optionally remove settings.
 *
 * Release checks: run both test modes on Windows; test 100/150/200% scaling,
 * high contrast, keyboard navigation, each protection option and combinations,
 * powercfg /requests before/during/after protection, expiry while minimized,
 * manual sleep/resume, duplicate launch, startup from paths containing spaces,
 * AC and battery/Modern Standby. The UI scales with system DPI at startup.
 * Shutdown release checks (use a disposable Windows VM with work saved):
 * enable only shutdown protection; try normal shutdown, restart and sign-out;
 * cancel each attempt and repeat with Awaken minimized. Confirm the Windows
 * reason is shown and cancellation keeps protection active. Repeat after Stop,
 * timer expiry and exit: Awaken must no longer block. Check startup --activate
 * with the saved option and repeat with all protections enabled. Verify force
 * termination/"Shut down anyway" overrides it; do not expect data preservation.
 * Cross-compilation and simulated tests cannot validate physical power behavior.
 * Binaries are unsigned; distribution signing requires your own certificate.
 */

#if defined(AWAKEN_RESOURCES)

#include <windows.h>
#ifdef AWAKEN_ICON_TEST_RESOURCE
/* A small synthetic icon verifies resource discovery without external .ico files.
 * BGRA = 44 99 11 ff; the group ID intentionally differs from IDI_APPLICATION. */
101 3
BEGIN
    40L, 1L, 2L, 1, 32, 0L, 4L, 0L, 0L, 0L, 0L, 0xff119944L, 0L
END
#ifdef AWAKEN_ICON_TEST_NUMERIC
321 14
#else
"AWAKEN_TEST_ICON" 14
#endif
BEGIN
    0, 1, 1, 0x0101, 0, 1, 32, 48L, 101
END
#endif
1 RT_MANIFEST
BEGIN
    "<?xml version=""1.0"" encoding=""UTF-8"" standalone=""yes""?>"
    "<assembly xmlns=""urn:schemas-microsoft-com:asm.v1"" manifestVersion=""1.0"">"
    "  <assemblyIdentity version=""1.0.0.0"" processorArchitecture=""*"" name=""YcK.Awaken"" type=""win32""/>"
    "  <description>Awaken desktop power protection</description>"
    "  <dependency><dependentAssembly>"
    "    <assemblyIdentity type=""win32"" name=""Microsoft.Windows.Common-Controls"" version=""6.0.0.0"" processorArchitecture=""*"" publicKeyToken=""6595b64144ccf1df"" language=""*""/>"
    "  </dependentAssembly></dependency>"
    "  <trustInfo xmlns=""urn:schemas-microsoft-com:asm.v3""><security><requestedPrivileges>"
    "    <requestedExecutionLevel level=""asInvoker"" uiAccess=""false""/>"
    "  </requestedPrivileges></security></trustInfo>"
    "  <application xmlns=""urn:schemas-microsoft-com:asm.v3""><windowsSettings>"
    "    <dpiAware xmlns=""http://schemas.microsoft.com/SMI/2005/WindowsSettings"">true</dpiAware>"
    "  </windowsSettings></application>"
    "  <compatibility xmlns=""urn:schemas-microsoft-com:compatibility.v1""><application>"
    "    <supportedOS Id=""{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}""/>"
    "  </application></compatibility>"
    "</assembly>"
END

1 VERSIONINFO
FILEVERSION 1,0,0,0
PRODUCTVERSION 1,0,0,0
FILEFLAGSMASK 0x3fL
FILEFLAGS 0
FILEOS VOS_NT_WINDOWS32
FILETYPE VFT_APP
BEGIN
  BLOCK "StringFileInfo"
  BEGIN
    BLOCK "040904b0"
    BEGIN
      VALUE "FileDescription", "Awaken\0"
      VALUE "FileVersion", "1.0.0\0"
      VALUE "ProductName", "Awaken\0"
      VALUE "ProductVersion", "1.0.0\0"
      VALUE "OriginalFilename", "awaken.exe\0"
    END
  END
  BLOCK "VarFileInfo"
  BEGIN
    VALUE "Translation", 0x0409, 1200
  END
END

#else /* C compilation */

#include <stdint.h>
#include <wchar.h>

/* argv[0] is a path, never an activation request. */
static int HasActivateArgument(int count, wchar_t **arguments) {
    int index;
    for (index = 1; index < count; ++index) {
        if (wcscmp(arguments[index], L"--activate") == 0) return 1;
    }
    return 0;
}

/* Index order is persisted in the registry; keep existing entries stable. */
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

static uint64_t RemainingSeconds(uint64_t milliseconds) {
    /* Round up without overflowing at UINT64_MAX. */
    return milliseconds / 1000 + (milliseconds % 1000 != 0);
}

/* Query handling must remain nonblocking, even when the expiry timer is delayed. */
static int ShouldBlockShutdown(int active, int registered, int critical,
                               uint64_t endsAt, uint64_t now) {
    return active && registered && !critical && (endsAt == 0 || now < endsAt);
}

#if defined(AWAKEN_LOGIC_TEST)

#include <stdio.h>
#include <stdlib.h>

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr, "Failed at line %d: %s\n", __LINE__, #condition); exit(1); \
} } while (0)

int main(void) {
    int durations[] = {0, 15, 30, 60, 120, 240, 480};
    wchar_t *pathOnly[] = {L"C:\\--activate\\awaken.exe"};
    wchar_t *partial[] = {L"awaken.exe", L"--activate-later"};
    wchar_t *embedded[] = {L"awaken.exe", L"prefix--activate"};
    wchar_t *exact[] = {L"C:\\Program Files\\Awaken.exe", L"--activate"};
    wchar_t *multiple[] = {L"awaken.exe", L"--unknown", L"--activate"};
    int index;
    for (index = 0; index < 7; ++index) CHECK(DurationMinutesFromSelection(index) == durations[index]);
    CHECK(DurationMinutesFromSelection(-1) == 0);
    CHECK(DurationMinutesFromSelection(7) == 0);
    CHECK(!HasActivateArgument(0, NULL));
    CHECK(!HasActivateArgument(1, pathOnly));
    CHECK(!HasActivateArgument(2, partial));
    CHECK(!HasActivateArgument(2, embedded));
    CHECK(HasActivateArgument(2, exact));
    CHECK(HasActivateArgument(3, multiple));
    CHECK(RemainingSeconds(0) == 0);
    CHECK(RemainingSeconds(1) == 1);
    CHECK(RemainingSeconds(999) == 1);
    CHECK(RemainingSeconds(1000) == 1);
    CHECK(RemainingSeconds(1001) == 2);
    CHECK(RemainingSeconds(28800000) == 28800);
    CHECK(RemainingSeconds(UINT64_MAX) == UINT64_MAX / 1000 + 1);
    CHECK(ShouldBlockShutdown(1, 1, 0, 0, UINT64_MAX));
    CHECK(ShouldBlockShutdown(1, 1, 0, 1000, 999));
    CHECK(!ShouldBlockShutdown(1, 1, 0, 1000, 1000));
    CHECK(!ShouldBlockShutdown(1, 1, 0, 1000, 1001));
    CHECK(!ShouldBlockShutdown(0, 1, 0, 0, 0));
    CHECK(!ShouldBlockShutdown(1, 0, 0, 0, 0));
    CHECK(!ShouldBlockShutdown(1, 1, 1, 0, 0));
    puts("Awaken logic tests passed");
    return 0;
}

#else /* Windows application or lifecycle tests */

#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif

#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include <commctrl.h>
#include <windowsx.h>
#include <strsafe.h>
#include <stdint.h>
#include <wchar.h>
#include <shellapi.h>
#include <string.h>

/* Older Windows SDK/MinGW headers may omit these documented session flags.
 * Keep SDK definitions when available; the message ABI values are fixed. */
#ifndef ENDSESSION_CRITICAL
#define ENDSESSION_CRITICAL 0x40000000
#endif
#ifndef ENDSESSION_CLOSEAPP
#define ENDSESSION_CLOSEAPP 0x00000001
#endif




#ifdef _MSC_VER
#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#endif

#ifdef AWAKEN_WINDOWS_TEST
#include <stdio.h>
#include <stdlib.h>
static BOOL failShutdownCreate, failShutdownDestroy;
static unsigned int shutdownCreates, shutdownDestroys;
static BOOL WINAPI TestShutdownCreate(HWND hwnd, LPCWSTR reason);
static BOOL WINAPI TestShutdownDestroy(HWND hwnd);
#define ShutdownBlockReasonCreate TestShutdownCreate
#define ShutdownBlockReasonDestroy TestShutdownDestroy
static BOOL failTimer, failExecution, failPower, failPowerCreate;
static BOOL failStandardControls, failAllControls;
static unsigned int controlInitCalls;
static unsigned int dialogs, requests, clears, executionCalls;
static EXECUTION_STATE lastExecution;
static int WINAPI TestMessageBoxW(HWND hwnd, LPCWSTR text, LPCWSTR title, UINT type);
static UINT_PTR WINAPI TestSetTimer(HWND hwnd, UINT_PTR id, UINT timeout, TIMERPROC callback);
static EXECUTION_STATE WINAPI TestExecutionState(EXECUTION_STATE flags);
static FARPROC WINAPI TestGetProcAddress(HMODULE module, LPCSTR name);
static BOOL WINAPI TestInitCommonControlsEx(const INITCOMMONCONTROLSEX *controls);

#define REGISTRY_SETTINGS_PATH L"Software\\AwakenRegressionTests\\Settings"
#define REGISTRY_RUN_PATH L"Software\\AwakenRegressionTests\\Run"
#define MessageBoxW TestMessageBoxW
#define SetTimer TestSetTimer
#define SetThreadExecutionState TestExecutionState
#define GetProcAddress TestGetProcAddress
#define InitCommonControlsEx TestInitCommonControlsEx
#endif

#define APP_CLASS_NAME             L"AwakenWindowClass"
#define APP_TITLE                  L"Awaken"
#ifndef REGISTRY_SETTINGS_PATH
#define REGISTRY_SETTINGS_PATH     L"Software\\Awaken"
#endif
#ifndef REGISTRY_RUN_PATH
#define REGISTRY_RUN_PATH          L"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
#endif
#define REGISTRY_RUN_VALUE         L"Awaken"

#define ID_CHECK_SYSTEM_SLEEP      1001
#define ID_CHECK_DISPLAY_OFF       1002
#define ID_CHECK_SCREENSAVER       1003
#define ID_COMBO_DURATION          1004
#define ID_CHECK_STARTUP           1005
#define ID_BUTTON_START            1006
#define ID_BUTTON_STOP             1007
#define ID_STATUS_TEXT             1008
#define ID_REMAINING_TEXT          1009
#define ID_CHECK_SHUTDOWN          1010
#define ID_TIMER_MAIN              2001

#define WINDOW_WIDTH               620
#define WINDOW_HEIGHT              676

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
    HWND checkShutdown;
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
    BOOL shutdownBlockApplied;
    BOOL executionStateApplied;
    HANDLE displayPowerRequestHandle;
    BOOL displayPowerRequestApplied;
    int dpi;
    BOOL interfaceFailed;

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

typedef struct IconLoadContext {
    int width;
    int height;
    HICON icon;
} IconLoadContext;

static BOOL CALLBACK LoadFirstIconResource(HMODULE module, LPCWSTR type, LPWSTR name, LONG_PTR parameter) {
    IconLoadContext *context = (IconLoadContext *)parameter;
    (void)type;
    /* Dev-C++ may use a named resource or a numeric ID. Do not assume either.
     * Owned handles avoid LR_SHARED returning the first cached size for both icons. */
    context->icon = (HICON)LoadImageW(module, name, IMAGE_ICON,
        context->width, context->height, LR_DEFAULTCOLOR);
    return context->icon == NULL;
}

/* Returns an owned icon. The caller must release it after destroying the window. */
static HICON LoadApplicationIcon(HINSTANCE instance, int width, int height) {
    IconLoadContext context = {width, height, NULL};
    EnumResourceNamesW(instance, RT_GROUP_ICON, LoadFirstIconResource, (LONG_PTR)&context);
    if (context.icon != NULL) return context.icon;

    /* A plain single-file build need not have an icon resource. Copy the shared
     * system icon so both the embedded and fallback paths have the same ownership. */
    return (HICON)CopyImage(LoadIconW(NULL, IDI_APPLICATION), IMAGE_ICON,
        width, height, 0);
}

static void DestroyApplicationIcons(HICON largeIcon, HICON smallIcon) {
    if (largeIcon != NULL) DestroyIcon(largeIcon);
    if (smallIcon != NULL) DestroyIcon(smallIcon);
}

static LRESULT CALLBACK WindowProc(HWND hwnd, UINT message, WPARAM wParam, LPARAM lParam);
static void StartProtection(HWND hwnd);
static BOOL StopProtection(HWND hwnd);
static void UpdateStatusText(void);
static void SaveSettings(void);

static int Scale(int value) {
    return MulDiv(value, g_app.dpi, 96);
}


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
        memcpy(&setProcessDPIAwareFunction, &procedureAddress, sizeof(setProcessDPIAwareFunction));
        (void)setProcessDPIAwareFunction();
    }
}

static BOOL ApplyPowerRequestDisplayRequired(void) {
    HMODULE kernel32Module;
    AppPowerCreateRequestFunction powerCreateRequest;
    AppPowerSetRequestFunction powerSetRequest;
    AppPowerReasonContext reasonContext;
    HANDLE requestHandle;
    FARPROC address;

    if (g_app.displayPowerRequestApplied) {
        return TRUE;
    }

    kernel32Module = GetModuleHandleW(L"kernel32.dll");
    if (kernel32Module == NULL) {
        return FALSE;
    }

    address = GetProcAddress(kernel32Module, "PowerCreateRequest");
    memcpy(&powerCreateRequest, &address, sizeof(powerCreateRequest));
    address = GetProcAddress(kernel32Module, "PowerSetRequest");
    memcpy(&powerSetRequest, &address, sizeof(powerSetRequest));

    if (powerCreateRequest == NULL || powerSetRequest == NULL) {
        return FALSE;
    }

    ZeroMemory(&reasonContext, sizeof(reasonContext));
    reasonContext.Version = APP_POWER_REQUEST_CONTEXT_VERSION;
    reasonContext.Flags = APP_POWER_REQUEST_CONTEXT_SIMPLE_STRING;
    reasonContext.Reason.SimpleReasonString =
        L"Awaken is preventing the screen saver and automatic display timeout.";

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
    FARPROC address;

    if (g_app.displayPowerRequestHandle == NULL) {
        g_app.displayPowerRequestApplied = FALSE;
        return;
    }

    kernel32Module = GetModuleHandleW(L"kernel32.dll");
    if (kernel32Module != NULL) {
        address = GetProcAddress(kernel32Module, "PowerClearRequest");
        memcpy(&powerClearRequest, &address, sizeof(powerClearRequest));

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
        Scale(x),
        Scale(y),
        Scale(width),
        Scale(height),
        parent,
        (HMENU)(INT_PTR)controlId,
        GetModuleHandleW(NULL),
        NULL
    );

    if (control == NULL) g_app.interfaceFailed = TRUE;

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

static BOOL WriteRegistryDword(HKEY key, LPCWSTR valueName, DWORD value) {
    return RegSetValueExW(key, valueName, 0, REG_DWORD,
        (const BYTE *)&value, sizeof(value)) == ERROR_SUCCESS;
}

static BOOL BuildStartupCommand(WCHAR *command, size_t count) {
    WCHAR path[MAX_PATH];
    DWORD length = GetModuleFileNameW(NULL, path, ARRAYSIZE(path));
    return length > 0 && length < ARRAYSIZE(path) &&
        SUCCEEDED(StringCchPrintfW(command, count, L"\"%s\" --activate", path));
}

static BOOL IsStartupEnabled(void) {
    HKEY key = NULL;
    WCHAR actual[MAX_PATH + 32] = {0};
    WCHAR expected[MAX_PATH + 32];
    DWORD type = 0;
    DWORD size = sizeof(actual);
    LONG result;

    if (!BuildStartupCommand(expected, ARRAYSIZE(expected))) return FALSE;
    result = RegOpenKeyExW(HKEY_CURRENT_USER, REGISTRY_RUN_PATH, 0, KEY_QUERY_VALUE, &key);
    if (result != ERROR_SUCCESS) return FALSE;
    result = RegQueryValueExW(key, REGISTRY_RUN_VALUE, NULL, &type, (LPBYTE)actual, &size);
    RegCloseKey(key);
    return result == ERROR_SUCCESS && type == REG_SZ &&
        size >= sizeof(WCHAR) && size <= sizeof(actual) && size % sizeof(WCHAR) == 0 &&
        actual[size / sizeof(WCHAR) - 1] == L'\0' && wcscmp(actual, expected) == 0;
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
        WCHAR commandLine[MAX_PATH + 32];
        if (!BuildStartupCommand(commandLine, ARRAYSIZE(commandLine))) {
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
    Button_SetCheck(g_app.checkShutdown, BST_UNCHECKED);

    if (ReadRegistryDword(L"PreventSystemSleep", &value)) {
        Button_SetCheck(g_app.checkSystemSleep, value ? BST_CHECKED : BST_UNCHECKED);
    }
    if (ReadRegistryDword(L"PreventDisplayOff", &value)) {
        Button_SetCheck(g_app.checkDisplayOff, value ? BST_CHECKED : BST_UNCHECKED);
    }
    if (ReadRegistryDword(L"PreventScreensaver", &value)) {
        Button_SetCheck(g_app.checkScreensaver, value ? BST_CHECKED : BST_UNCHECKED);
    }
    if (ReadRegistryDword(L"PreventShutdown", &value)) {
        Button_SetCheck(g_app.checkShutdown, value ? BST_CHECKED : BST_UNCHECKED);
    }
    if (ReadRegistryDword(L"DurationIndex", &value) && value <= 6) {
        durationIndex = (int)value;
    }

    ComboBox_SetCurSel(g_app.comboDuration, durationIndex);
    Button_SetCheck(g_app.checkStartup, IsStartupEnabled() ? BST_CHECKED : BST_UNCHECKED);
}

static void SaveSettings(void) {
    HKEY key = NULL;
    BOOL saved = TRUE;
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
        MessageBoxW(g_app.hwnd, L"Settings could not be saved. Changes apply only to this session.",
            APP_TITLE, MB_OK | MB_ICONWARNING);
        return;
    }

    saved = WriteRegistryDword(
        key,
        L"PreventSystemSleep",
        Button_GetCheck(g_app.checkSystemSleep) == BST_CHECKED
    ) && saved;
    saved = WriteRegistryDword(
        key,
        L"PreventDisplayOff",
        Button_GetCheck(g_app.checkDisplayOff) == BST_CHECKED
    ) && saved;
    saved = WriteRegistryDword(
        key,
        L"PreventScreensaver",
        Button_GetCheck(g_app.checkScreensaver) == BST_CHECKED
    ) && saved;
    saved = WriteRegistryDword(key, L"PreventShutdown",
        Button_GetCheck(g_app.checkShutdown) == BST_CHECKED) && saved;
    saved = WriteRegistryDword(
        key,
        L"DurationIndex",
        (DWORD)ComboBox_GetCurSel(g_app.comboDuration)
    ) && saved;

    RegCloseKey(key);
    if (!saved) {
        MessageBoxW(g_app.hwnd, L"Some settings could not be saved. Check them next time you launch Awaken.",
            APP_TITLE, MB_OK | MB_ICONWARNING);
    }
}

static void SetConfigurationControlsEnabled(BOOL enabled) {
    EnableWindow(g_app.checkSystemSleep, enabled);
    EnableWindow(g_app.checkDisplayOff, enabled);
    EnableWindow(g_app.checkScreensaver, enabled);
    EnableWindow(g_app.checkShutdown, enabled);
    EnableWindow(g_app.comboDuration, enabled);
    EnableWindow(g_app.buttonStart, enabled);
    EnableWindow(g_app.buttonStop, !enabled);
}

static void FormatRemainingTime(ULONGLONG milliseconds, WCHAR *buffer, size_t bufferCount) {
    ULONGLONG totalSeconds = RemainingSeconds(milliseconds);
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
        SetWindowTextW(g_app.statusText, L"Inactive - Windows power settings are in effect");
        SetWindowTextW(g_app.remainingText, L"Protection is not active");
        InvalidateRect(g_app.statusText, NULL, TRUE);
        return;
    }

    SetWindowTextW(g_app.statusText, L"Active - Selected protection is running");

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
    BOOL preventShutdown = Button_GetCheck(g_app.checkShutdown) == BST_CHECKED;
    EXECUTION_STATE executionFlags = ES_CONTINUOUS;
    int durationMinutes;

    if (g_app.active) {
        return;
    }

    if (!preventSystemSleep && !preventDisplayOff && !preventScreensaver && !preventShutdown) {
        MessageBoxW(
            hwnd,
            L"Select at least one protection option.",
            APP_TITLE,
            MB_OK | MB_ICONINFORMATION
        );
        return;
    }

    g_app.executionStateApplied = FALSE;

    if (preventScreensaver) {
        if (!ApplyPowerRequestDisplayRequired()) {
            MessageBoxW(hwnd,
                L"Screen saver protection could not be applied. No protection was started. "
                L"Try again or deselect the screen saver option.",
                APP_TITLE, MB_OK | MB_ICONERROR);
            return;
        }
    }

    if (preventSystemSleep) {
        executionFlags |= ES_SYSTEM_REQUIRED;
    }
    if (preventDisplayOff) {
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

    if (preventShutdown) {
        if (!ShutdownBlockReasonCreate(hwnd,
                L"Awaken protection is active. Stop protection in Awaken to end this session.")) {
            if (!StopProtection(hwnd)) return;
            MessageBoxW(hwnd, L"Shutdown protection could not be registered. No protection is active.",
                APP_TITLE, MB_OK | MB_ICONERROR);
            return;
        }
        g_app.shutdownBlockApplied = TRUE;
    }

    durationMinutes = DurationMinutesFromSelection(ComboBox_GetCurSel(g_app.comboDuration));
    g_app.startedAt = GetTickCount64();
    g_app.endsAt = durationMinutes > 0
        ? g_app.startedAt + ((ULONGLONG)durationMinutes * 60ULL * 1000ULL)
        : 0;
    if (SetTimer(hwnd, ID_TIMER_MAIN, 1000, NULL) == 0) {
        if (!StopProtection(hwnd)) return;
        MessageBoxW(hwnd, L"The protection timer could not be started. No protection is active.",
            APP_TITLE, MB_OK | MB_ICONERROR);
        return;
    }
    g_app.active = TRUE;

    SetConfigurationControlsEnabled(FALSE);
    SetFocus(g_app.buttonStop);
    SaveSettings();
    UpdateStatusText();
}

static BOOL StopProtection(HWND hwnd) {
    BOOL wasActive = g_app.active;
    KillTimer(hwnd, ID_TIMER_MAIN);

    if (g_app.executionStateApplied) {
        if (SetThreadExecutionState(ES_CONTINUOUS) == 0) {
            /* Keep the stop action available; do not claim a failed release worked.
             * The timer is stopped to avoid repeated error dialogs on expiry. */
            g_app.active = TRUE;
            SetConfigurationControlsEnabled(FALSE);
            SetWindowTextW(g_app.statusText, L"Protection could not be stopped");
            SetWindowTextW(g_app.remainingText, L"Try Stop again, or close Awaken to release protection");
            MessageBoxW(hwnd, L"Windows could not release protection. Try Stop again or close Awaken.",
                APP_TITLE, MB_OK | MB_ICONERROR);
            return FALSE;
        }
        g_app.executionStateApplied = FALSE;
    }

    ClearPowerRequestDisplayRequired();
    if (g_app.shutdownBlockApplied) {
        if (!ShutdownBlockReasonDestroy(hwnd)) {
            g_app.active = TRUE;
            SetConfigurationControlsEnabled(FALSE);
            SetWindowTextW(g_app.statusText, L"Shutdown protection could not be stopped");
            SetWindowTextW(g_app.remainingText, L"Try Stop again, or close Awaken to release protection");
            MessageBoxW(hwnd, L"Windows could not release shutdown protection. Try Stop again or close Awaken.",
                APP_TITLE, MB_OK | MB_ICONERROR);
            return FALSE;
        }
        g_app.shutdownBlockApplied = FALSE;
    }

    g_app.active = FALSE;
    g_app.startedAt = 0;
    g_app.endsAt = 0;

    SetConfigurationControlsEnabled(TRUE);
    if (wasActive) SetFocus(g_app.buttonStart);
    UpdateStatusText();
    return TRUE;
}

static void CreateFonts(void) {
    int dpiY = g_app.dpi;

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
        L"Keep Windows awake for a task, then return to your normal power settings.",
        WS_CHILD | WS_VISIBLE,
        30, 66, 550, 42,
        hwnd, 0, g_app.fontNormal
    );
    (void)subtitle;

    groupProtection = CreateControl(
        0, L"BUTTON", L"Protection options",
        WS_CHILD | WS_VISIBLE | BS_GROUPBOX,
        26, 112, 558, 214,
        hwnd, 0, g_app.fontNormal
    );
    (void)groupProtection;

    g_app.checkSystemSleep = CreateControl(
        0, L"BUTTON", L"Prevent automatic &sleep",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
        48, 145, 500, 28,
        hwnd, ID_CHECK_SYSTEM_SLEEP, g_app.fontNormal
    );

    g_app.checkDisplayOff = CreateControl(
        0, L"BUTTON", L"Keep the &display on",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
        48, 183, 500, 28,
        hwnd, ID_CHECK_DISPLAY_OFF, g_app.fontNormal
    );

    g_app.checkScreensaver = CreateControl(
        0, L"BUTTON", L"Prevent screen sa&ver (also keeps the display on)",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
        48, 221, 500, 28,
        hwnd, ID_CHECK_SCREENSAVER, g_app.fontNormal
    );

    g_app.checkShutdown = CreateControl(
        0, L"BUTTON", L"Block shutdown, &restart and sign-out",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
        48, 259, 500, 28,
        hwnd, ID_CHECK_SHUTDOWN, g_app.fontNormal
    );

    durationLabel = CreateControl(
        0, L"STATIC", L"D&uration:",
        WS_CHILD | WS_VISIBLE,
        48, 296, 120, 24,
        hwnd, 0, g_app.fontNormal
    );
    (void)durationLabel;

    g_app.comboDuration = CreateControl(
        0, L"COMBOBOX", L"",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST | WS_VSCROLL,
        174, 292, 210, 250,
        hwnd, ID_COMBO_DURATION, g_app.fontNormal
    );

    ComboBox_AddString(g_app.comboDuration, L"Unlimited - until stopped");
    ComboBox_AddString(g_app.comboDuration, L"15 minutes");
    ComboBox_AddString(g_app.comboDuration, L"30 minutes");
    ComboBox_AddString(g_app.comboDuration, L"1 hour");
    ComboBox_AddString(g_app.comboDuration, L"2 hours");
    ComboBox_AddString(g_app.comboDuration, L"4 hours");
    ComboBox_AddString(g_app.comboDuration, L"8 hours");

    groupBehavior = CreateControl(
        0, L"BUTTON", L"Application",
        WS_CHILD | WS_VISIBLE | BS_GROUPBOX,
        26, 340, 558, 74,
        hwnd, 0, g_app.fontNormal
    );
    (void)groupBehavior;

    g_app.checkStartup = CreateControl(
        0, L"BUTTON", L"Start Awaken with &Windows and activate protection",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
        48, 368, 500, 28,
        hwnd, ID_CHECK_STARTUP, g_app.fontNormal
    );

    g_app.statusText = CreateControl(
        0, L"STATIC", L"",
        WS_CHILD | WS_VISIBLE,
        30, 436, 555, 28,
        hwnd, ID_STATUS_TEXT, g_app.fontButton
    );

    g_app.remainingText = CreateControl(
        0, L"STATIC", L"",
        WS_CHILD | WS_VISIBLE,
        30, 464, 555, 24,
        hwnd, ID_REMAINING_TEXT, g_app.fontNormal
    );

    g_app.buttonStart = CreateControl(
        0, L"BUTTON", L"&Activate",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_DEFPUSHBUTTON,
        30, 500, 266, 42,
        hwnd, ID_BUTTON_START, g_app.fontButton
    );

    g_app.buttonStop = CreateControl(
        0, L"BUTTON", L"S&top",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
        312, 500, 266, 42,
        hwnd, ID_BUTTON_STOP, g_app.fontButton
    );

    note = CreateControl(
        0, L"STATIC",
        L"Manual sleep, screen lock and lid actions still work. Display protection alone does not prevent sleep.",
        WS_CHILD | WS_VISIBLE,
        30, 554, 555, 36,
        hwnd, 0, g_app.fontSmall
    );
    (void)note;

    CreateControl(0, L"STATIC",
        L"Shutdown protection also blocks restart and sign-out. Forced shutdown and power loss can override it.",
        WS_CHILD | WS_VISIBLE, 30, 592, 555, 36, hwnd, 0, g_app.fontSmall);

    footer = CreateControl(
        0, L"STATIC", L"Settings are stored in your user account; administrator privileges are not required.",
        WS_CHILD | WS_VISIBLE,
        30, 630, 555, 36,
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
            if (g_app.interfaceFailed || !g_app.backgroundBrush || !g_app.fontNormal ||
                !g_app.fontSmall || !g_app.fontTitle || !g_app.fontButton) return -1;
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
                 controlId == ID_CHECK_SCREENSAVER ||
                 controlId == ID_CHECK_SHUTDOWN) &&
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
                    if (StopProtection(hwnd)) {
                        SetWindowTextW(g_app.remainingText, L"Duration ended - normal power settings restored");
                    }
                } else {
                    UpdateStatusText();
                }
                return 0;
            }
            break;

        case WM_POWERBROADCAST:
            /* Windows can discard power requests during user-initiated sleep.
             * Stop the session instead of reporting stale protection on resume. */
            if (wParam == PBT_APMSUSPEND && g_app.active) {
                if (StopProtection(hwnd)) {
                    SetWindowTextW(g_app.remainingText, L"Stopped for system sleep - activate to start again");
                }
            }
            return TRUE;

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

        case WM_QUERYENDSESSION:
            /* Never show dialogs or release protection during a query: another
             * application or the user can still cancel the shutdown. Critical
             * termination cannot reliably be vetoed by a desktop application. */
            return ShouldBlockShutdown(g_app.active, g_app.shutdownBlockApplied,
                (lParam & ENDSESSION_CRITICAL) != 0, g_app.endsAt, GetTickCount64())
                ? FALSE : TRUE;

        case WM_ENDSESSION:
            if (wParam) {
                KillTimer(hwnd, ID_TIMER_MAIN);
                g_app.active = FALSE;
                if (g_app.shutdownBlockApplied) {
                    ShutdownBlockReasonDestroy(hwnd);
                    g_app.shutdownBlockApplied = FALSE;
                }
                if (g_app.executionStateApplied) {
                    SetThreadExecutionState(ES_CONTINUOUS);
                    g_app.executionStateApplied = FALSE;
                }
                ClearPowerRequestDisplayRequired();
            }
            return 0;

        case WM_DESTROY:
            /* Destroying the owning window also removes its shutdown reason. */
            if (g_app.shutdownBlockApplied) {
                ShutdownBlockReasonDestroy(hwnd);
                g_app.shutdownBlockApplied = FALSE;
            }
            g_app.active = FALSE;
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

/* ICC_STANDARD_CLASSES may be unavailable without the v6 manifest. The
 * standard buttons, labels and combo box can still use the classic controls. */
static BOOL InitializeInterfaceControls(void) {
    INITCOMMONCONTROLSEX controls;
    controls.dwSize = sizeof(controls);
    controls.dwICC = ICC_STANDARD_CLASSES;
    if (InitCommonControlsEx(&controls)) return TRUE;
    controls.dwICC = ICC_WIN95_CLASSES;
    return InitCommonControlsEx(&controls);
}

static void ShowStartupError(LPCWSTR operation, DWORD error) {
    WCHAR message[768];
    WCHAR detail[512] = L"";
    if (error != ERROR_SUCCESS) {
        FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
            NULL, error, 0, detail, ARRAYSIZE(detail), NULL);
        StringCchPrintfW(message, ARRAYSIZE(message),
            L"%s\nWindows error %lu: %s", operation, (unsigned long)error, detail);
    } else {
        StringCchCopyW(message, ARRAYSIZE(message), operation);
    }
    MessageBoxW(NULL, message, APP_TITLE, MB_OK | MB_ICONERROR);
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
    RECT windowRect = {0, 0, WINDOW_WIDTH, WINDOW_HEIGHT};
    BOOL activateOnLaunch;
    BOOL getMessageResult;
    HICON largeIcon;
    HICON smallIcon;
    HANDLE instanceMutex;
    WCHAR **arguments;
    int argumentCount;
    HDC screen;

    (void)previousInstance;
    (void)commandLine;
    arguments = CommandLineToArgvW(GetCommandLineW(), &argumentCount);
    if (arguments == NULL) {
        ShowStartupError(L"Awaken could not read its command line.", GetLastError());
        return 1;
    }
    activateOnLaunch = HasActivateArgument(argumentCount, arguments);
    LocalFree(arguments);

    /* One owner per interactive session prevents invisible competing requests. */
    instanceMutex = CreateMutexW(NULL, FALSE, L"Local\\Awaken.Instance");
    if (instanceMutex == NULL) {
        ShowStartupError(L"Awaken could not initialize its instance lock.", GetLastError());
        return 1;
    }
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        HWND existing = FindWindowW(APP_CLASS_NAME, NULL);
        if (existing != NULL) {
            ShowWindow(existing, SW_RESTORE);
            SetForegroundWindow(existing);
        } else {
            ShowStartupError(L"Another Awaken instance is running, but its window is not ready. "
                L"Wait a moment and try again. If it remains unavailable, close the existing "
                L"Awaken process in Task Manager before reopening it.", ERROR_SUCCESS);
            CloseHandle(instanceMutex);
            return 1;
        }
        CloseHandle(instanceMutex);
        return 0;
    }

    ZeroMemory(&g_app, sizeof(g_app));
    EnableDpiAwarenessIfSupported();
    screen = GetDC(NULL);
    g_app.dpi = screen != NULL ? GetDeviceCaps(screen, LOGPIXELSY) : 96;
    if (screen != NULL) ReleaseDC(NULL, screen);
    if (g_app.dpi <= 0) g_app.dpi = 96;
    windowRect.right = Scale(WINDOW_WIDTH);
    windowRect.bottom = Scale(WINDOW_HEIGHT);

    SetLastError(ERROR_SUCCESS);
    if (!InitializeInterfaceControls()) {
        ShowStartupError(L"Awaken could not initialize the Windows interface controls.", GetLastError());
        CloseHandle(instanceMutex);
        return 1;
    }

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
        ShowStartupError(L"The application window class could not be registered.", GetLastError());
        DestroyApplicationIcons(largeIcon, smallIcon);
        CloseHandle(instanceMutex);
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
        ShowStartupError(L"The application window could not be created.", GetLastError());
        UnregisterClassW(APP_CLASS_NAME, instance);
        DestroyApplicationIcons(largeIcon, smallIcon);
        CloseHandle(instanceMutex);
        return 1;
    }

    SendMessageW(hwnd, WM_SETICON, ICON_BIG, (LPARAM)largeIcon);
    SendMessageW(hwnd, WM_SETICON, ICON_SMALL, (LPARAM)smallIcon);

    /* A launcher may request SW_HIDE; Awaken has no tray UI to recover it. */
    ShowWindow(hwnd, showCommand == SW_HIDE ? SW_SHOWNORMAL : showCommand);
    UpdateWindow(hwnd);

    if (activateOnLaunch) {
        StartProtection(hwnd);
    }

    while ((getMessageResult = (BOOL)GetMessageW(&message, NULL, 0, 0)) > 0) {
        if (!IsDialogMessageW(hwnd, &message)) {
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
    }

    if (getMessageResult == -1) {
        ShowStartupError(L"The Windows message loop failed.", GetLastError());
    }
    if (IsWindow(hwnd)) DestroyWindow(hwnd);
    UnregisterClassW(APP_CLASS_NAME, instance);
    DestroyApplicationIcons(largeIcon, smallIcon);
    CloseHandle(instanceMutex);
    return getMessageResult == -1 ? 1 : (int)message.wParam;
}

#ifdef AWAKEN_WINDOWS_TEST

#undef ShutdownBlockReasonCreate
#undef ShutdownBlockReasonDestroy
#undef MessageBoxW
#undef SetTimer
#undef SetThreadExecutionState
#undef GetProcAddress
#undef InitCommonControlsEx

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr, "Failed at line %d: %s\n", __LINE__, #condition); exit(1); \
} } while (0)

static BOOL WINAPI TestShutdownCreate(HWND hwnd, LPCWSTR reason) {
    CHECK(IsWindow(hwnd) && reason != NULL && reason[0] != L'\0');
    if (failShutdownCreate) return FALSE;
    ++shutdownCreates;
    return TRUE;
}

static BOOL WINAPI TestShutdownDestroy(HWND hwnd) {
    CHECK(IsWindow(hwnd));
    if (failShutdownDestroy) return FALSE;
    ++shutdownDestroys;
    return TRUE;
}

static BOOL WINAPI TestInitCommonControlsEx(const INITCOMMONCONTROLSEX *controls) {
    ++controlInitCalls;
    if (failAllControls || (failStandardControls && controls->dwICC == ICC_STANDARD_CLASSES)) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }
    return InitCommonControlsEx(controls);
}

static void CheckIcon(HICON icon, int width, int height) {
    ICONINFO info;
    BITMAP bitmap;
    CHECK(icon != NULL);
    CHECK(GetIconInfo(icon, &info));
    CHECK(GetObjectW(info.hbmColor, sizeof(bitmap), &bitmap) == sizeof(bitmap));
    CHECK(bitmap.bmWidth == width && bitmap.bmHeight == height);
#ifdef AWAKEN_ICON_TEST_RESOURCE
    {
        HDC dc = CreateCompatibleDC(NULL);
        HGDIOBJ previous;
        CHECK(dc != NULL);
        previous = SelectObject(dc, info.hbmColor);
        CHECK(GetPixel(dc, 0, 0) == RGB(17, 153, 68));
        SelectObject(dc, previous);
        DeleteDC(dc);
    }
#endif
    DeleteObject(info.hbmColor);
    DeleteObject(info.hbmMask);
}

static void TestApplicationIcons(void) {
    HINSTANCE instance = GetModuleHandleW(NULL);
    HICON largeIcon = LoadApplicationIcon(instance, 32, 32);
    HICON smallIcon = LoadApplicationIcon(instance, 16, 16);
    CheckIcon(largeIcon, 32, 32);
    CheckIcon(smallIcon, 16, 16);
    CHECK(largeIcon != smallIcon);
    DestroyApplicationIcons(largeIcon, smallIcon);
}

/* Exercise the real entry point and message loop, not just control creation. */
static DWORD WINAPI CloseStartupWindow(LPVOID unused) {
    unsigned int attempt;
    (void)unused;
    for (attempt = 0; attempt < 100; ++attempt) {
        HWND window = FindWindowW(APP_CLASS_NAME, NULL);
        if (window != NULL && IsWindowVisible(window)) {
            CheckIcon((HICON)SendMessageW(window, WM_GETICON, ICON_BIG, 0),
                GetSystemMetrics(SM_CXICON), GetSystemMetrics(SM_CYICON));
            CheckIcon((HICON)SendMessageW(window, WM_GETICON, ICON_SMALL, 0),
                GetSystemMetrics(SM_CXSMICON), GetSystemMetrics(SM_CYSMICON));
            CHECK(GetClassLongPtrW(window, GCLP_HICON) != 0);
            CHECK(GetClassLongPtrW(window, GCLP_HICONSM) != 0);
            PostMessageW(window, WM_CLOSE, 0, 0);
            return 0;
        }
        Sleep(50);
    }
    /* Avoid hanging the test forever when a regression creates a hidden window. */
    {
        HWND window = FindWindowW(APP_CLASS_NAME, NULL);
        if (window != NULL) PostMessageW(window, WM_CLOSE, 0, 0);
    }
    return 1;
}

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

/* Verify real API registration independently of the failure-injection stubs. */
static void TestShutdownReasonApi(HWND hwnd) {
    WCHAR reason[256];
    DWORD count = ARRAYSIZE(reason);
    CHECK(ShutdownBlockReasonCreate(hwnd, L"Awaken regression test"));
    CHECK(ShutdownBlockReasonQuery(hwnd, reason, &count));
    CHECK(wcscmp(reason, L"Awaken regression test") == 0);
    CHECK(ShutdownBlockReasonDestroy(hwnd));
}

/* These tests send session messages only; they never shut down the test host. */
static void TestShutdownProtection(HWND hwnd) {
    unsigned int before;
    CHECK(Button_GetCheck(g_app.checkShutdown) == BST_UNCHECKED);
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0, 0) == TRUE);
    SelectOptions(FALSE, FALSE, FALSE);
    Button_SetCheck(g_app.checkShutdown, BST_CHECKED);
    failShutdownCreate = TRUE;
    before = dialogs;
    StartProtection(hwnd);
    CHECK(!g_app.active && !g_app.shutdownBlockApplied && dialogs == before + 1);
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0, 0) == TRUE);
    SelectOptions(TRUE, TRUE, TRUE);
    StartProtection(hwnd);
    CHECK(!g_app.active && !g_app.executionStateApplied && requests == clears);
    failShutdownCreate = FALSE;
    SelectOptions(FALSE, FALSE, FALSE);
    failTimer = TRUE;
    StartProtection(hwnd);
    CHECK(!g_app.active && !g_app.shutdownBlockApplied && shutdownCreates == shutdownDestroys);
    failTimer = FALSE;

    ComboBox_SetCurSel(g_app.comboDuration, 0);
    StartProtection(hwnd);
    CHECK(g_app.active && g_app.shutdownBlockApplied);
    CHECK(!IsWindowEnabled(g_app.checkShutdown));
    before = shutdownCreates;
    StartProtection(hwnd);
    CHECK(shutdownCreates == before);
    before = dialogs;
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0, 0) == FALSE);
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0, ENDSESSION_LOGOFF) == FALSE);
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0, ENDSESSION_CLOSEAPP) == FALSE);
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0,
        ENDSESSION_CLOSEAPP | ENDSESSION_LOGOFF) == FALSE);
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0, ENDSESSION_CRITICAL) == TRUE);
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0,
        ENDSESSION_CRITICAL | ENDSESSION_LOGOFF | ENDSESSION_CLOSEAPP) == TRUE);
    CHECK(dialogs == before);
    SendMessageW(hwnd, WM_ENDSESSION, FALSE, 0);
    CHECK(g_app.active && g_app.shutdownBlockApplied);
    ShowWindow(hwnd, SW_MINIMIZE);
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0, 0) == FALSE);
    ShowWindow(hwnd, SW_HIDE);

    failShutdownDestroy = TRUE;
    CHECK(!StopProtection(hwnd));
    CHECK(g_app.active && g_app.shutdownBlockApplied && IsWindowEnabled(g_app.buttonStop));
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0, 0) == FALSE);
    failShutdownDestroy = FALSE;
    CHECK(StopProtection(hwnd));
    CHECK(!g_app.shutdownBlockApplied && shutdownCreates == shutdownDestroys);
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0, 0) == TRUE);
    CHECK(StopProtection(hwnd));
    CHECK(shutdownCreates == shutdownDestroys);

    ComboBox_SetCurSel(g_app.comboDuration, 1);
    StartProtection(hwnd);
    g_app.endsAt = GetTickCount64();
    CHECK(SendMessageW(hwnd, WM_QUERYENDSESSION, 0, 0) == TRUE);
    SendMessageW(hwnd, WM_TIMER, ID_TIMER_MAIN, 0);
    CHECK(!g_app.active && !g_app.shutdownBlockApplied);
    StartProtection(hwnd);
    SendMessageW(hwnd, WM_POWERBROADCAST, PBT_APMSUSPEND, 0);
    CHECK(!g_app.active && !g_app.shutdownBlockApplied);

    StartProtection(hwnd);
    SendMessageW(hwnd, WM_ENDSESSION, TRUE, ENDSESSION_CRITICAL);
    CHECK(!g_app.active && !g_app.shutdownBlockApplied);
    CHECK(shutdownCreates == shutdownDestroys);
    SetConfigurationControlsEnabled(TRUE);
    SaveSettings();
    Button_SetCheck(g_app.checkShutdown, BST_UNCHECKED);
    LoadSettings();
    CHECK(Button_GetCheck(g_app.checkShutdown) == BST_CHECKED);
    Button_SetCheck(g_app.checkShutdown, BST_UNCHECKED);
    SaveSettings();
    Button_SetCheck(g_app.checkShutdown, BST_CHECKED);
    LoadSettings();
    CHECK(Button_GetCheck(g_app.checkShutdown) == BST_UNCHECKED);
}

int main(void) {
    WNDCLASSW cls = {0};
    HANDLE closer;
    DWORD closeResult;
    MSG pending;
    HWND hwnd;
    unsigned int before;
    WCHAR text[128];
    HKEY key;
    DWORD invalid = 99;
    CHECK(InitializeInterfaceControls());
    TestApplicationIcons();
    failStandardControls = TRUE;
    controlInitCalls = 0;
    CHECK(InitializeInterfaceControls());
    CHECK(controlInitCalls == 2);
    failAllControls = TRUE;
    CHECK(!InitializeInterfaceControls());
    CHECK(controlInitCalls == 4);
    before = dialogs;
    CHECK(WinMain(GetModuleHandleW(NULL), NULL, NULL, SW_SHOWNORMAL) == 1);
    CHECK(dialogs == before + 1);
    failAllControls = FALSE;
    failStandardControls = FALSE;
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

    TestShutdownReasonApi(hwnd);
    TestShutdownProtection(hwnd);
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
    CHECK(StopProtection(hwnd));
    Button_SetCheck(g_app.checkShutdown, BST_CHECKED);
    StartProtection(hwnd);
    CHECK(g_app.shutdownBlockApplied);
    DestroyWindow(hwnd);
    CHECK(!g_app.shutdownBlockApplied && shutdownCreates == shutdownDestroys);
    CHECK(requests == clears && lastExecution == ES_CONTINUOUS);
    /* WM_DESTROY posted WM_QUIT; start the entry-point smoke test with a clean queue. */
    while (PeekMessageW(&pending, NULL, 0, 0, PM_REMOVE)) { }
    failStandardControls = TRUE;
    closer = CreateThread(NULL, 0, CloseStartupWindow, NULL, 0, NULL);
    CHECK(closer != NULL);
    before = dialogs;
    CHECK(WinMain(GetModuleHandleW(NULL), NULL, NULL, SW_HIDE) == 0);
    CHECK(WaitForSingleObject(closer, 10000) == WAIT_OBJECT_0);
    CHECK(GetExitCodeThread(closer, &closeResult) && closeResult == 0);
    CHECK(dialogs == before);
    CloseHandle(closer);
    failStandardControls = FALSE;
    CHECK(RegDeleteKeyW(HKEY_CURRENT_USER, REGISTRY_SETTINGS_PATH) == ERROR_SUCCESS);
    CHECK(RegDeleteKeyW(HKEY_CURRENT_USER, REGISTRY_RUN_PATH) == ERROR_SUCCESS);
    CHECK(RegDeleteKeyW(HKEY_CURRENT_USER, L"Software\\AwakenRegressionTests") == ERROR_SUCCESS);
    puts("Awaken Windows lifecycle tests passed");
    return 0;
}

#endif /* AWAKEN_WINDOWS_TEST */
#endif /* AWAKEN_LOGIC_TEST */
#endif /* AWAKEN_RESOURCES */
