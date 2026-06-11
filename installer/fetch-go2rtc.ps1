#Requires -Version 7.0
<#
.SYNOPSIS
    Download go2rtc Windows binary into installer/redist/go2rtc/ for Inno Setup packaging.

.EXAMPLE
    pwsh installer/fetch-go2rtc.ps1
    pwsh installer/fetch-go2rtc.ps1 -Version 1.9.14
#>
param(
    [string]$Version = '1.9.14'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$DestDir = Join-Path $PSScriptRoot 'redist\go2rtc'
$ExePath = Join-Path $DestDir 'go2rtc.exe'
$ZipUrl = "https://github.com/AlexxIT/go2rtc/releases/download/v$Version/go2rtc_win64.zip"
$ZipPath = Join-Path ([System.IO.Path]::GetTempPath()) "go2rtc_win64_$Version.zip"

New-Item -ItemType Directory -Force -Path $DestDir | Out-Null

Write-Host "Downloading go2rtc v$Version ..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath

Write-Host "Extracting to $DestDir ..." -ForegroundColor Cyan
if (Test-Path $ExePath) { Remove-Item $ExePath -Force }
Expand-Archive -Path $ZipPath -DestinationPath $DestDir -Force
Remove-Item $ZipPath -Force

if (-not (Test-Path $ExePath)) {
    throw "go2rtc.exe not found after extract. Check zip layout at $DestDir"
}

Write-Host "OK: $ExePath" -ForegroundColor Green
