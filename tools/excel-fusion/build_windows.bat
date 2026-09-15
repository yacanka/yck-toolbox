@echo off
setlocal DisableDelayedExpansion
pushd "%~dp0"
if errorlevel 1 exit /b 1

py -3.12 -c "import sys" >nul 2>&1
if errorlevel 1 goto use_python
py -3.12 build_windows.py
goto finished

:use_python
python -c "import sys" >nul 2>&1
if errorlevel 1 goto missing_python
python build_windows.py
goto finished

:missing_python
echo Python bulunamadi. Python 3.12 x64 kurun; Tcl/Tk ve PATH seceneklerini etkinlestirin.
set "build_exit=1"
goto cleanup

:finished
set "build_exit=%errorlevel%"

:cleanup
if not "%build_exit%"=="0" echo Paketleme basarisiz. Yukaridaki hata mesajini kontrol edin.
popd
if /I not "%~1"=="--no-pause" pause
exit /b %build_exit%
