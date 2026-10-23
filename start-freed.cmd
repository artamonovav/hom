@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-freed.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo Launcher exited with code %RC%.
  pause
)
exit /b %RC%
