#requires -Version 5.1
$ErrorActionPreference = "Stop"

$Root = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$pidFile = Join-Path $Root ".freed-server.pid"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host "No .freed-server.pid found."
    Write-Host "If the server was started in the current console, press Ctrl+C there."
    exit 0
}

$serverPid = [int](Get-Content -LiteralPath $pidFile | Select-Object -First 1)
$process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue

if ($process -and ($process.ProcessName -like "powershell*" -or $process.ProcessName -like "pwsh*" -or $process.ProcessName -like "python*")) {
    Stop-Process -Id $serverPid -Force
    Write-Host "Stopped Freed server (PID $serverPid)."
}
else {
    Write-Host "PID $serverPid is not a running server process; removing stale PID file."
}

Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
