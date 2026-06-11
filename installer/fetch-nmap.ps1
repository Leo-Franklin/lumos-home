#Requires -Version 7.0
<#
.SYNOPSIS
    Populate installer/redist/nmap/ with Nmap Windows binaries.

    Tries silent NSIS install into redist/nmap, then falls back to copying
    from an existing system install under Program Files.
#>
param(
    [string]$Version = '7.95'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$DestDir = Join-Path $PSScriptRoot 'redist\nmap'
$DestExe = Join-Path $DestDir 'nmap.exe'

function Copy-NmapFromSource {
    param([string]$SourceDir)
    if (-not (Test-Path (Join-Path $SourceDir 'nmap.exe'))) {
        return $false
    }
    if (Test-Path $DestDir) { Remove-Item $DestDir -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    Copy-Item -Path (Join-Path $SourceDir '*') -Destination $DestDir -Recurse -Force
    return $true
}

if (Test-Path $DestExe) {
    Write-Host "Already present: $DestExe" -ForegroundColor Yellow
    return
}

New-Item -ItemType Directory -Force -Path $DestDir | Out-Null

$SetupUrl = "https://nmap.org/dist/nmap-$Version-setup.exe"
$SetupPath = Join-Path ([System.IO.Path]::GetTempPath()) "nmap-$Version-setup.exe"

Write-Host "Downloading nmap $Version setup ..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $SetupUrl -OutFile $SetupPath

# NSIS: /D= must be last and use a path without trailing backslash
$InstallDir = (Resolve-Path $DestDir).Path
Write-Host "Silent install to $InstallDir ..." -ForegroundColor Cyan
$proc = Start-Process -FilePath $SetupPath -ArgumentList @('/S', "/D=$InstallDir") -Wait -PassThru
Remove-Item $SetupPath -Force -ErrorAction SilentlyContinue

if (Test-Path $DestExe) {
    Write-Host "OK: $DestExe" -ForegroundColor Green
    return
}

Write-Host 'Silent install did not place nmap.exe; trying Program Files copy ...' -ForegroundColor Yellow
$Candidates = @(
    "${env:ProgramFiles(x86)}\Nmap",
    "$env:ProgramFiles\Nmap"
)
foreach ($dir in $Candidates) {
    if (Copy-NmapFromSource -SourceDir $dir) {
        Write-Host "OK (copied from $dir): $DestExe" -ForegroundColor Green
        return
    }
}

throw @"
nmap.exe still missing under $DestDir.
Install Nmap once from https://nmap.org/download.html, then re-run:
  pwsh installer/fetch-nmap.ps1
"@
