#Requires -Version 7.0
<#
.SYNOPSIS
    One-click build script for Lumos Home Windows installer.
    Run from the lumos-home\ root directory.

.PREREQUISITES
    - Node.js (for frontend build)
    - Python 3.11 + uv (for backend packaging)
    - PyInstaller (uv add --dev pyinstaller in backend\)
    - Inno Setup 6 (iscc must be in PATH)
    - installer\redist\npcap.exe   (Npcap OEM installer)
    - installer\redist\ffmpeg.exe  (ffmpeg Windows single-file build)
    - installer\redist\nmap\       (nmap Windows portable)
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = $PSScriptRoot | Split-Path  # lumos-home\ root
$FrontendDir = Join-Path $Root 'frontend'
$BackendDir = Join-Path $Root 'backend'
$InstallerDir = Join-Path $Root 'installer'

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
