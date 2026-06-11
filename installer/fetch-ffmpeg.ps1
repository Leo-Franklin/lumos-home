#Requires -Version 7.0
<#
.SYNOPSIS
    Download ffmpeg essentials build into installer/redist/ffmpeg.exe
#>
param(
    [string]$ZipUrl = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$DestExe = Join-Path $PSScriptRoot 'redist\ffmpeg.exe'
$ZipPath = Join-Path ([System.IO.Path]::GetTempPath()) 'lumos-ffmpeg-essentials.zip'
$ExtractRoot = Join-Path ([System.IO.Path]::GetTempPath()) 'lumos-ffmpeg-extract'

New-Item -ItemType Directory -Force -Path (Split-Path $DestExe) | Out-Null

if (Test-Path $DestExe) {
    Write-Host "Already present: $DestExe" -ForegroundColor Yellow
    return
}

Write-Host 'Downloading ffmpeg essentials build ...' -ForegroundColor Cyan
Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath

if (Test-Path $ExtractRoot) { Remove-Item $ExtractRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $ExtractRoot | Out-Null
Expand-Archive -Path $ZipPath -DestinationPath $ExtractRoot -Force
Remove-Item $ZipPath -Force

$FfmpegBin = Get-ChildItem -Path $ExtractRoot -Recurse -Filter 'ffmpeg.exe' -File | Select-Object -First 1
if (-not $FfmpegBin) {
    throw "ffmpeg.exe not found inside extracted archive ($ExtractRoot)"
}

Copy-Item -Path $FfmpegBin.FullName -Destination $DestExe -Force
Remove-Item $ExtractRoot -Recurse -Force

Write-Host "OK: $DestExe" -ForegroundColor Green
