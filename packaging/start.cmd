@echo off
setlocal
cd /d "%~dp0"
title Honda Freed - local manual
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"
"%PS%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve-freed.ps1" -Root "%~dp0site" -Open -Quiet
if errorlevel 1 pause
