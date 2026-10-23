#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8000,

    [switch]$NoBrowser,

    [switch]$NewWindow
)

$ErrorActionPreference = 'Stop'

$Root = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$Site = Join-Path $Root 'site'
$Server = Join-Path $Root 'serve-freed.ps1'

if (-not (Test-Path -LiteralPath $Server)) {
    Write-Host "ERROR: serve-freed.ps1 was not found next to this script." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path -LiteralPath (Join-Path $Site 'index.html'))) {
    Write-Host ""
    Write-Host "ERROR: site/index.html was not found." -ForegroundColor Red
    Write-Host "Build the offline site first (Linux/WSL):"
    Write-Host "  cd $Root"
    Write-Host "  make all-years"
    Write-Host ""
    exit 1
}

if ($NewWindow) {
    $argLine = '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + $Server + '" -Root "' + $Site + '" -Port ' + $Port + ' -Quiet'
    if (-not $NoBrowser) {
        $argLine += ' -Open'
    }

    $process = Start-Process -FilePath 'powershell.exe' -ArgumentList $argLine -WorkingDirectory $Root -PassThru
    Set-Content -LiteralPath (Join-Path $Root '.freed-server.pid') -Value $process.Id -Encoding ASCII
    Start-Sleep -Milliseconds 1200

    Write-Host "Honda Freed - local owner's manual" -ForegroundColor Cyan
    Write-Host "  Server PID: $($process.Id)"
    Write-Host "  Stop with stop-freed.cmd or close the server window."
    exit 0
}

$serverArgs = @{
    Root = $Site
    Port = $Port
    Quiet = $true
}
if (-not $NoBrowser) {
    $serverArgs.Open = $true
}

& $Server @serverArgs
