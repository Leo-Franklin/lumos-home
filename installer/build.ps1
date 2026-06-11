#Requires -Version 7.0
<#
.SYNOPSIS
    One-click build script for Lumos Home Windows installer.
    Run from the lumos-home\ root directory.

.PARAMETER FetchRedist
    Download missing redistributables via fetch-redist.ps1 before building.

.PREREQUISITES
    - Node.js (for frontend build)
    - Python 3.11 + uv (for backend packaging)
    - PyInstaller (uv add --dev pyinstaller in backend\)
    - Inno Setup 6 (iscc must be in PATH)
    - installer\redist\  (run: pwsh installer/fetch-redist.ps1)
#>
param(
    [switch]$FetchRedist
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = $PSScriptRoot | Split-Path  # lumos-home\ root
$FrontendDir = Join-Path $Root 'frontend'
$BackendDir = Join-Path $Root 'backend'
$InstallerDir = Join-Path $Root 'installer'

function Test-RedistPresent {
    $Required = @(
        (Join-Path $InstallerDir 'redist\ffmpeg.exe'),
        (Join-Path $InstallerDir 'redist\npcap.exe'),
        (Join-Path $InstallerDir 'redist\nmap\nmap.exe'),
        (Join-Path $InstallerDir 'redist\go2rtc\go2rtc.exe')
    )
    return ,@($Required | Where-Object { -not (Test-Path $_) })
}

Write-Host "=== Step 0: Check redistributables ===" -ForegroundColor Cyan
$Missing = Test-RedistPresent
if ($Missing.Count -gt 0 -and $FetchRedist) {
    Write-Host 'Missing redist — running fetch-redist.ps1 ...' -ForegroundColor Yellow
    & (Join-Path $InstallerDir 'fetch-redist.ps1')
    $Missing = Test-RedistPresent
}
if ($Missing.Count -gt 0) {
    Write-Host 'Missing installer redistributables:' -ForegroundColor Red
    foreach ($path in $Missing) {
        Write-Host "  - $path" -ForegroundColor Red
    }
    Write-Host '' -ForegroundColor Red
    Write-Host 'Run from repo root:' -ForegroundColor Yellow
    Write-Host '  pwsh installer/fetch-redist.ps1' -ForegroundColor Yellow
    Write-Host 'Or build with auto-fetch:' -ForegroundColor Yellow
    Write-Host '  pwsh installer/build.ps1 -FetchRedist' -ForegroundColor Yellow
    throw 'Install missing redist files before building the installer.'
}

Write-Host "=== Step 1: Build frontend ===" -ForegroundColor Cyan
Push-Location $FrontendDir
try {
    npm run build
} finally {
    Pop-Location
}

Write-Host "=== Step 2: Copy frontend dist to backend ===" -ForegroundColor Cyan
$DistDir = Join-Path $FrontendDir 'dist'
$FrontendDest = Join-Path $BackendDir 'frontend'
if (Test-Path $FrontendDest) { Remove-Item $FrontendDest -Recurse -Force }
Copy-Item $DistDir $FrontendDest -Recurse

Write-Host "=== Step 3: Package backend with PyInstaller ===" -ForegroundColor Cyan
Push-Location $BackendDir
try {
    uv run pyinstaller lumos-home.spec --clean
} finally {
    Pop-Location
}

Write-Host "=== Step 4: Build installer with Inno Setup ===" -ForegroundColor Cyan
$IssFile = Join-Path $InstallerDir 'installer.iss'
iscc $IssFile

Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Installer: $InstallerDir\output\LumosHome-Setup.exe"
