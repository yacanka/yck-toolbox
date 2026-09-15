# Compatibility entry point. Packaging is maintained in BAT/Python.
& "$PSScriptRoot\build_windows.bat" --no-pause
exit $LASTEXITCODE
