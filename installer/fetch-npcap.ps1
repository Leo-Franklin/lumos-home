#Requires -Version 7.0
<#
.SYNOPSIS
    Download Npcap installer into installer/redist/npcap.exe for Inno Setup.

.NOTES
    Public redistribution requires Npcap OEM (https://npcap.com/oem/).
    This script is for local / internal installer builds only.
#>
param(
    [string]$Version = '1.88'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$DestExe = Join-Path $PSScriptRoot 'redist\npcap.exe'
$Url = "https://npcap.com/dist/npcap-$Version.exe"

New-Item -ItemType Directory -Force -Path (Split-Path $DestExe) | Out-Null

if (Test-Path $DestExe) {
    Write-Host "Already present: $DestExe" -ForegroundColor Yellow
    return
}

Write-Host "Downloading Npcap $Version ..." -ForegroundColor Cyan
Write-Host 'Note: public redistribution requires Npcap OEM license.' -ForegroundColor Yellow
Invoke-WebRequest -Uri $Url -OutFile $DestExe

if (-not (Test-Path $DestExe)) {
    throw "Download failed: $DestExe"
}

Write-Host "OK: $DestExe" -ForegroundColor Green
