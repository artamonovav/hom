#requires -Version 5.1
<#
    Local static server for the offline Honda Freed manual.

    Windows 10/11 only needs the built-in PowerShell 5.1 and .NET Framework:
    no Python, no admin rights, no external binaries.  The server listens on
    127.0.0.1 and serves the "site" directory.

    It also contains a small fallback for the translated tree: some Honda
    scripts build relative URLs such as /ru/.../freed/asset/... without the
    year segment.  If the exact file is missing, the server tries the Japanese
    tree, inserts the year from the Referer header, or tries the available
    years.  This is the same behaviour as serve.py on Linux.
#>
[CmdletBinding()]
param(
    [string]$Root,
    [int]$Port = 8000,
    [string]$Bind = '127.0.0.1',
    [switch]$Open,
    [string]$Page = 'index.html',
    [switch]$Quiet,
    [string]$RequestLog
)

$ErrorActionPreference = 'Stop'

if (-not $Root) {
    $scriptDir = $PSScriptRoot
    if (-not $scriptDir -and $MyInvocation.MyCommand.Path) {
        $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    }
    if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
    $Root = Join-Path $scriptDir 'site'
}
$Root = [IO.Path]::GetFullPath($Root)
if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
    throw "Site root not found: $Root"
}
if (-not (Test-Path -LiteralPath (Join-Path $Root 'index.html') -PathType Leaf)) {
    throw "site/index.html not found under $Root"
}

$mime = @{
    '.html'  = 'text/html; charset=utf-8'
    '.htm'   = 'text/html; charset=utf-8'
    '.css'   = 'text/css; charset=utf-8'
    '.js'    = 'text/javascript; charset=utf-8'
    '.mjs'   = 'text/javascript; charset=utf-8'
    '.json'  = 'application/json; charset=utf-8'
    '.map'   = 'application/json; charset=utf-8'
    '.xml'   = 'text/xml; charset=utf-8'
    '.xsl'   = 'text/xml; charset=utf-8'
    '.svg'   = 'image/svg+xml'
    '.svgz'  = 'image/svg+xml'
    '.txt'   = 'text/plain; charset=utf-8'
    '.csv'   = 'text/csv; charset=utf-8'
    '.pdf'   = 'application/pdf'
    '.gif'   = 'image/gif'
    '.png'   = 'image/png'
    '.jpg'   = 'image/jpeg'
    '.jpeg'  = 'image/jpeg'
    '.webp'  = 'image/webp'
    '.bmp'   = 'image/bmp'
    '.ico'   = 'image/x-icon'
    '.cur'   = 'image/x-icon'
    '.woff'  = 'font/woff'
    '.woff2' = 'font/woff2'
    '.ttf'   = 'font/ttf'
    '.otf'   = 'font/otf'
    '.eot'   = 'application/vnd.ms-fontobject'
    '.mp4'   = 'video/mp4'
    '.webm'  = 'video/webm'
    '.mp3'   = 'audio/mpeg'
    '.wav'   = 'audio/wav'
    '.ogg'   = 'audio/ogg'
    '.swf'   = 'application/x-shockwave-flash'
}

function Get-Mime([string]$ext) {
    if ($ext -and $mime.ContainsKey($ext.ToLowerInvariant())) {
        return $mime[$ext.ToLowerInvariant()]
    }
    return 'application/octet-stream'
}

function Get-Url([int]$p) {
    return 'http://' + $Bind + ':' + $p + '/'
}

$listener = $null

function Test-FreedServer([int]$p) {
    try {
        $req = [Net.WebRequest]::Create((Get-Url $p) + $Page)
        $req.Timeout = 2000
        $req.ReadWriteTimeout = 2000
        $req.Proxy = $null
        $resp = $req.GetResponse()
        $reader = New-Object IO.StreamReader ($resp.GetResponseStream())
        $html = $reader.ReadToEnd()
        $reader.Close()
        $resp.Close()
        return (($html -match 'Honda') -or ($html -match 'Freed'))
    }
    catch {
        return $false
    }
}

# If another copy is already serving this page, just open it.
for ($p = $Port; $p -le $Port + 10; $p++) {
    if (Test-FreedServer $p) {
        Write-Host ('Freed manual: server already running at ' + (Get-Url $p)) -ForegroundColor Green
        if ($Open) {
            Start-Process ((Get-Url $p) + $Page) | Out-Null
        }
        exit 0
    }

    $candidate = New-Object System.Net.HttpListener
    $candidate.Prefixes.Add((Get-Url $p))
    try {
        $candidate.Start()
        $listener = $candidate
        $Port = $p
        break
    }
    catch {
        try { $candidate.Close() } catch { }
    }
}

if (-not $listener) {
    Write-Host ('Cannot bind ports ' + $Port + '..' + ($Port + 10) + '. Use -Port to choose another.') -ForegroundColor Red
    exit 1
}

$url = Get-Url $Port
Write-Host ''
Write-Host "Honda Freed - local owner's manual" -ForegroundColor Cyan
Write-Host ('  URL:  ' + $url) -ForegroundColor Green
Write-Host ('  Site: ' + $Root)
Write-Host '  Stop: close this window or press Ctrl+C'
Write-Host ''

if ($Open) {
    $openUrl = $url + $Page
    Write-Host ('Opening ' + $openUrl)
    Start-Process $openUrl | Out-Null
}

$rootFull = $Root.TrimEnd([char[]]@('\', '/'))

function Test-Inside([string]$full) {
    return (($full.StartsWith($rootFull + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) -or
            ($full -eq $rootFull))
}

function Get-FilePath([string]$urlPath) {
    $rel = [Uri]::UnescapeDataString($urlPath)
    $rel = $rel.TrimStart('/')
    $rel = $rel.Replace('/', [IO.Path]::DirectorySeparatorChar)

    if ([string]::IsNullOrEmpty($rel)) {
        $full = $rootFull
    }
    else {
        $full = [IO.Path]::GetFullPath((Join-Path $rootFull $rel))
    }
    if (-not (Test-Inside $full)) { return $null }
    if (Test-Path -LiteralPath $full -PathType Leaf) { return $full }
    if (Test-Path -LiteralPath $full -PathType Container) {
        $index = Join-Path $full 'index.html'
        if (Test-Path -LiteralPath $index -PathType Leaf) { return $index }
    }
    return $null
}

function Get-RefererYear([string]$referer) {
    if (-not $referer) { return $null }
    $m = [regex]::Match($referer, '/(\d{4})(?:/|$)')
    if ($m.Success) { return $m.Groups[1].Value }
    return $null
}

function Insert-Year([string]$path, [string]$year) {
    $m = [regex]::Match($path, '^(/ru)?(/ownersmanual/webom/jpn/[^/]+/)(.*)$')
    if (-not $m.Success) { return $null }
    $tail = $m.Groups[3].Value
    if ($tail -match '^\d{4}(/|$)') { return $path }
    if (-not $year) { return $null }
    return $m.Groups[1].Value + $m.Groups[2].Value + $year + '/' + $tail
}

function Get-YearCandidates([string]$path) {
    $m = [regex]::Match($path, '^(/ru)?(/ownersmanual/webom/jpn/[^/]+/)(.*)$')
    if (-not $m.Success) { return @() }
    $tail = $m.Groups[3].Value
    if ($tail -match '^\d{4}(/|$)') { return @() }

    $prefix = $m.Groups[1].Value + $m.Groups[2].Value
    $dirRel = $m.Groups[2].Value.TrimStart('/').Replace('/', [IO.Path]::DirectorySeparatorChar)
    $dir = Join-Path $rootFull $dirRel
    $result = @()
    if (Test-Path -LiteralPath $dir -PathType Container) {
        foreach ($d in Get-ChildItem -LiteralPath $dir -Directory) {
            if ($d.Name -match '^\d{4}$') {
                $result += $prefix + $d.Name + '/' + $tail
            }
        }
    }
    return $result
}

function Resolve-FreedPath([string]$urlPath, [string]$referer) {
    $path = [Uri]::UnescapeDataString($urlPath)
    $candidates = New-Object System.Collections.Generic.List[string]
    $candidates.Add($path)

    $stripped = $null
    if ($path.StartsWith('/ru/')) {
        $stripped = $path.Substring(3)
        $candidates.Add($stripped)
    }
    else {
        $candidates.Add('/ru' + $path)
    }

    $year = Get-RefererYear $referer
    $bases = @($path)
    if ($stripped) { $bases += $stripped }
    else { $bases += ('/ru' + $path) }

    foreach ($base in $bases) {
        $inserted = Insert-Year $base $year
        if ($inserted) { $candidates.Add($inserted) }
        foreach ($yc in (Get-YearCandidates $base)) {
            $candidates.Add($yc)
        }
    }

    foreach ($candidate in $candidates) {
        $file = Get-FilePath $candidate
        if ($file) { return $file }
    }
    return $null
}

try {
    while ($listener.IsListening) {
        $ctx = $listener.GetContext()
        $req = $ctx.Request
        $res = $ctx.Response

        try {
            $referer = $req.Headers['Referer']
            $full = Resolve-FreedPath $req.Url.AbsolutePath $referer

            if (-not $full) {
                $res.StatusCode = 404
                $res.ContentType = 'text/plain; charset=utf-8'
                $res.Headers.Add('Cache-Control', 'no-store')
                $body = [Text.Encoding]::UTF8.GetBytes('404 ' + $req.Url.PathAndQuery)
                $res.ContentLength64 = $body.Length
                if ($req.HttpMethod -ne 'HEAD') {
                    $res.OutputStream.Write($body, 0, $body.Length)
                }
            }
            else {
                $ext = [IO.Path]::GetExtension($full)
                $extLower = $ext.ToLowerInvariant()
                $fileInfo = [IO.FileInfo]::new($full)
                $res.StatusCode = 200
                $res.ContentType = Get-Mime $ext
                $res.Headers.Add('Last-Modified', $fileInfo.LastWriteTimeUtc.ToString('R'))
                if (@('.html', '.htm', '.js', '.mjs', '.json', '.css', '.xml', '.txt') -contains $extLower) {
                    $res.Headers.Add('Cache-Control', 'no-cache')
                }
                else {
                    $res.Headers.Add('Cache-Control', 'public, max-age=86400')
                }

                $notModified = $false
                $ifModifiedSince = $req.Headers['If-Modified-Since']
                if ($ifModifiedSince) {
                    try {
                        $since = [DateTime]::Parse($ifModifiedSince, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::AdjustToUniversal)
                        if ($fileInfo.LastWriteTimeUtc -le $since.AddSeconds(1)) {
                            $notModified = $true
                        }
                    }
                    catch { }
                }

                if ($notModified) {
                    $res.StatusCode = 304
                    $res.ContentLength64 = 0
                }
                else {
                    if ($extLower -eq '.svgz' -and -not $req.QueryString['raw']) {
                        $res.Headers.Add('Content-Encoding', 'gzip')
                    }
                    $res.ContentLength64 = $fileInfo.Length
                    if ($req.HttpMethod -ne 'HEAD') {
                        $stream = [IO.File]::OpenRead($full)
                        try {
                            $stream.CopyTo($res.OutputStream, 65536)
                        }
                        finally {
                            $stream.Dispose()
                        }
                    }
                }
            }
        }
        catch {
            try {
                $res.StatusCode = 500
                $res.ContentType = 'text/plain; charset=utf-8'
                $res.Headers.Add('Cache-Control', 'no-store')
                $body = [Text.Encoding]::UTF8.GetBytes('500 ' + $_.Exception.Message)
                $res.ContentLength64 = $body.Length
                if ($req.HttpMethod -ne 'HEAD') {
                    $res.OutputStream.Write($body, 0, $body.Length)
                }
            }
            catch { }
        }
        finally {
            if (-not $Quiet) {
                Write-Host ($req.HttpMethod + ' ' + $res.StatusCode + ' ' + $req.Url.PathAndQuery)
            }
            if ($RequestLog) {
                try {
                    Add-Content -LiteralPath $RequestLog -Encoding UTF8 -Value ($req.HttpMethod + ' ' + $res.StatusCode + ' ' + $req.Url.PathAndQuery)
                }
                catch { }
            }
            try { $res.Close() } catch { }
        }
    }
}
finally {
    try { $listener.Stop() } catch { }
    try { $listener.Close() } catch { }
    Write-Host 'Server stopped'
}
