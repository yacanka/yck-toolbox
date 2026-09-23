# Awaken

A small native Windows utility that temporarily requests protection from automatic
sleep, display timeout, and screen saver activation. No administrator privileges,
network connection, background service, or third-party runtime is required.

## Use

1. Run `awaken.exe` and select the protection you need.
2. Choose unlimited, 15 or 30 minutes, or 1, 2, 4 or 8 hours.
3. Select **Activate**. **Stop**, closing the window, or the deadline releases protection.

Minimizing keeps protection active; closing exits. Expiry updates the status without
an interrupting dialog. Tab / Shift+Tab navigate controls; Space toggles options.
Alt+A activates, Alt+T stops, Alt+D toggles display protection, and Alt+U opens the
duration control. Only one instance runs per Windows session; launching another
copy brings the existing window forward without restarting its timer.

`awaken.exe --activate` starts protection with the saved options and a fresh duration.
Only a separate, exact `--activate` argument is recognized; other arguments are
ignored. The Windows startup checkbox registers the quoted executable path plus
this argument in the current user's Run key. Disable it before moving or removing
the executable, then enable it again from the new location.

### Protection boundaries

- **Prevent automatic sleep** requests that the system remain awake.
- **Keep the display on** requests that automatic display timeout be suppressed.
- **Prevent screen saver** also keeps the display on. This Windows API cannot
  provide screen saver suppression independently of display protection.
- Select sleep protection as well if the computer must keep running. Display-only
  protection does not independently prevent system sleep.
- Manual sleep, shutdown, screen locking, lid actions, and organizational policies
  remain effective. Awaken does not simulate input or change global power/security
  settings. Windows can override requests, especially on battery / Modern Standby.
- When Windows sends a suspend notification, the session ends. Activate again after
  resume. A deadline uses elapsed monotonic time rather than the wall clock.
- A failed protection request or timer setup never silently falls back to a weaker
  protection mode. The application reports the failure and releases acquired requests.

API references: [SetThreadExecutionState](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate),
[PowerSetRequest](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-powersetrequest),
[power request types](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ne-wdm-_power_request_type).

## Build on Windows

Requires CMake 3.20+ and Visual Studio 2022 with the Desktop development with C++
workload (including the Windows SDK). Run from a developer terminal:

```powershell
cmake -S tools/awaken -B tools/awaken/build -A x64
cmake --build tools/awaken/build --config Release
ctest --test-dir tools/awaken/build -C Release --output-on-failure
cmake --install tools/awaken/build --config Release --prefix tools/awaken/dist
```

Use `-A Win32` in a separate build directory for x86. The install directory contains
`awaken.exe` and this guide. The executable embeds its manifest/version metadata,
runs as the current user, and statically links compiler support libraries
(MSVC also uses its static C runtime; MinGW uses the Windows Universal CRT). No missing icon files or
resource headers need to be supplied. A standard Windows icon is used.

Windows 10/11 are the intended deployment targets. Older Windows versions have not
been qualified. The UI is system-DPI-aware: controls and fonts scale together at
startup; Windows handles scaling between monitors. Restart after changing the
primary display scaling for crisp rendering.

### MinGW cross-build (macOS/Linux)

With MinGW-w64 and Ninja installed:

```sh
cmake -S tools/awaken -B tools/awaken/build-windows -G Ninja \
  -DCMAKE_SYSTEM_NAME=Windows \
  -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc \
  -DCMAKE_RC_COMPILER=x86_64-w64-mingw32-windres \
  -DCMAKE_BUILD_TYPE=Release
cmake --build tools/awaken/build-windows
```

Use `i686-w64-mingw32-*` for x86. Windows executables cannot be executed natively on
macOS/Linux. Portable logic tests can run there using CMake without the cross-build
options. Build outputs are ignored by Git.

## Validation

`.github/workflows/awaken.yml` builds x64/x86 with MSVC, runs both test suites and
uploads executable/README artifacts. Linux also runs the portable tests. Warnings
are treated as errors. CI runs when this directory changes or by manual dispatch.

- `test_logic.c`: argument boundaries, all duration presets, invalid selections,
  rounding and 64-bit overflow boundaries.
- `test_windows.c`: real Win32 controls with simulated power/timer calls; empty
  selection, request creation/application failures, rollback, duplicate activation,
  expiry, unlimited duration, failed/repeated stop, suspend and window destruction. Settings
  and startup registration use `HKCU\Software\AwakenRegressionTests`, never the real
  Windows Run key. The test removes its registry keys on success.

Before distributing a release, run the Windows CI tests and this hardware/UI smoke
check on Windows 10/11:

1. At 100%, 150%, and 200% scaling, verify every label/control is visible, tab order
   works, and status/remaining time remain readable. Also check high contrast mode.
2. Exercise each option alone and together; verify `powercfg /requests` while active
   and after Stop, expiry, window close and process termination.
3. With short Windows idle timeouts, check real display/sleep/screen saver behavior.
   Include AC power and battery/Modern Standby; power policy can override requests.
4. Test expiry while minimized, manual sleep/resume, and a second launch.
5. Enable startup from a path containing spaces, sign out/in, verify activation,
   then disable startup and confirm the Run entry is removed.

Current local verification (2026-09-23): x64 and x86 MinGW release builds passed
with `-Wall -Wextra -Werror`; GCC static analysis reported no issues; portable
logic tests passed on macOS. Windows lifecycle tests were compiled for both
architectures but have not been executed here. MSVC CI and the hardware/UI smoke
checks above remain unverified until run on Windows.

Cross-compilation and simulated tests do not establish actual hardware power
behavior. Release binaries are unsigned; signing requires the distributor's own
certificate and is not configured in this repository.

## Settings and removal

Existing settings remain compatible in `HKCU\Software\IAmAwake`. Startup uses the
`IAmAwake` value under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
Registry write failures are reported; the current session remains usable.

Disable startup, close Awaken, then remove its executable to uninstall. Its small
per-user settings key can optionally be removed. No services or machine-wide
power settings are installed.
