#Requires -Version 7.0
<#
.SYNOPSIS
    Download / prepare all installer redistributables under installer/redist/.

.EXAMPLE
    pwsh installer/fetch-redist.ps1
    pwsh installer/fetch-redist.ps1 -SkipNpcap   # if you will copy npcap.exe manually
#>
param(
    [switch]$SkipNpcap
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$InstallerDir = $PSScriptRoot

Write-Host '=== Fetch installer redistributables ===' -ForegroundColor Cyan

& (Join-Path $InstallerDir 'fetch-ffmpeg.ps1')
& (Join-Path $InstallerDir 'fetch-go2rtc.ps1')
& (Join-Path $InstallerDir 'fetch-nmap.ps1')

if (-not $SkipNpcap) {
    & (Join-Path $InstallerDir 'fetch-npcap.ps1')
} else {
    Write-Host 'Skipped Npcap download (-SkipNpcap). Place npcap.exe manually.' -ForegroundColor Yellow
}

Write-Host ''
Write-Host '=== Redist status ===' -ForegroundColor Cyan
$Checks = @(
    'redist\ffmpeg.exe',
    'redist\npcap.exe',
    'redist\nmap\nmap.exe',
    'redist\go2rtc\go2rtc.exe'
)
$AllOk = $true
foreach ($rel in $Checks) {
    $path = Join-Path $InstallerDir $rel
    if (Test-Path $path) {
        Write-Host "  OK  $rel" -ForegroundColor Green
    } else {
        Write-Host "  MISSING  $rel" -ForegroundColor Red
        $AllOk = $false
    }
}

if (-not $AllOk) {
    throw 'Some redistributables are still missing. See messages above.'
}

Write-Host ''
Write-Host 'All redistributables ready. Run: pwsh installer/build.ps1' -ForegroundColor Green
