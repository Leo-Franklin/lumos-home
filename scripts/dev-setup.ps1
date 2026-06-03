#Requires -Version 7.0
<#
.SYNOPSIS
    Dev-only helper: create a relative symlink at backend/frontend pointing
    to frontend/dist so the FastAPI dev server can serve the built SPA.

.DESCRIPTION
    The production build (installer/build.ps1) copies frontend/dist into
    backend/frontend/ at packaging time. For local development, this
    helper creates a relative symlink at backend/frontend/ that points
    back to ../../frontend/dist. Re-run after `pnpm build` if the
    symlink gets out of sync.

.NOTES
    Run from the repo root. Idempotent — safe to re-run.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = $PSScriptRoot | Split-Path -Parent
$LinkPath = Join-Path $RepoRoot 'backend/frontend'
$Target = Join-Path $RepoRoot 'frontend/dist'

# Ensure dist exists
if (-not (Test-Path $Target)) {
    Write-Host "frontend/dist/ not found. Run 'pnpm --dir frontend build' first." -ForegroundColor Yellow
    exit 1
}

# Remove existing entry (file, dir, broken symlink)
if (Test-Path $LinkPath) {
    $item = Get-Item $LinkPath -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        # It's a symlink — remove the link itself, not the target
        (Get-Item $LinkPath -Force).Delete()
    } elseif ($item.PSIsContainer) {
        Remove-Item $LinkPath -Recurse -Force
    } else {
        Remove-Item $LinkPath -Force
    }
}

# New-Item -ItemType SymbolicLink requires admin OR developer mode on Windows.
# Fall back to a junction if symlink creation fails.
try {
    New-Item -ItemType SymbolicLink -Path $LinkPath -Target $Target -ErrorAction Stop | Out-Null
    Write-Host "Created symlink: $LinkPath -> $Target" -ForegroundColor Green
} catch {
    Write-Host "Symlink failed (need admin or Developer Mode). Falling back to junction." -ForegroundColor Yellow
    New-Item -ItemType Junction -Path $LinkPath -Target $Target | Out-Null
    Write-Host "Created junction: $LinkPath -> $Target" -ForegroundColor Green
}

Write-Host "Done. Restart the backend dev server to pick up the static mount." -ForegroundColor Cyan
