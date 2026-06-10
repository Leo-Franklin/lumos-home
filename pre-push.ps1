#!/usr/bin/env pwsh
# pre-push.ps1 - Git push 前统一检查脚本 (前端 + 后端)
#
# 用法:
#   ./pre-push.ps1              # 严格镜像 CI (不修改文件)
#   ./pre-push.ps1 -Fix         # 先 ruff --fix + format,再跑检查
#   ./pre-push.ps1 -InstallHook # 安装 git pre-push hook,之后每次 push 自动跑本脚本
#
# 默认行为与 .github/workflows/ci.yml 一致,不自动改文件。
# 若使用 -Fix 产生了未提交改动,脚本会失败并提示先 commit,避免"本地过了、CI 挂了"。
#
# frontend/.prettierrc.json 使用 "endOfLine": "auto",Windows CRLF 与 Linux LF 均可通过 prettier --check。

[CmdletBinding()]
param(
    [switch]$Fix,
    [switch]$InstallHook,
    [switch]$BackendOnly
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

if ($InstallHook) {
    $hookPath = Join-Path $RepoRoot ".git/hooks/pre-push"
    $hookBody = @"
#!/bin/sh
# Installed by pre-push.ps1 -InstallHook
exec pwsh -NoProfile -File "$RepoRoot/pre-push.ps1"
"@
    $hookBody | Set-Content -Path $hookPath -Encoding utf8NoBOM
    Write-Host "Installed git pre-push hook -> $hookPath" -ForegroundColor Green
    Write-Host "Every 'git push' will now run ./pre-push.ps1 first." -ForegroundColor Green
    exit 0
}

# 必填环境变量 (后端 pytest 需要,与 ci.yml 一致)
$env:JWT_SECRET_KEY = 'test_secret_key_that_is_at_least_32_characters_long'
$env:ADMIN_PASSWORD = 'testpassword_for_ci_only'
$env:CORS_ALLOW_ORIGINS = 'http://localhost:5173'

$script:failures = @()
$script:warnings = @()

function Test-RepoDirty {
    param([string[]]$Paths)
    Push-Location $RepoRoot
    try {
        $diff = git diff --name-only -- @Paths 2>$null
        $untracked = git ls-files --others --exclude-standard -- @Paths 2>$null
        return @($diff + $untracked | Where-Object { $_ })
    } finally {
        Pop-Location
    }
}

function Invoke-Step {
    param(
        [string]$Label,
        [scriptblock]$Action,
        [switch]$WarnOnly
    )
    Write-Host "`n[$Label]" -ForegroundColor Cyan
    & $Action
    $exit = $LASTEXITCODE
    if ($null -eq $exit) { $exit = 0 }
    if ($exit -ne 0) {
        if ($WarnOnly) {
            $script:warnings += $Label
            Write-Host "[WARN] $Label (exit=$exit)" -ForegroundColor Yellow
        } else {
            $script:failures += $Label
            Write-Host "[FAIL] $Label (exit=$exit)" -ForegroundColor Red
        }
    } else {
        Write-Host "[OK] $Label" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=== Pre-Push Checks (frontend + backend) ===" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot" -ForegroundColor DarkGray
if ($Fix) {
    Write-Host "Mode: -Fix (auto-fix then verify)" -ForegroundColor Yellow
} else {
    Write-Host "Mode: strict CI mirror (no file changes)" -ForegroundColor DarkGray
}

# ── Backend ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "---- Backend ----" -ForegroundColor Magenta

Push-Location (Join-Path $RepoRoot "backend")
try {
    if ($Fix) {
        Invoke-Step "backend auto-fix (ruff)" {
            uv run ruff check --fix app/ tests/
            if ($LASTEXITCODE -ne 0) { return }
            uv run ruff format app/ tests/
        }

        $dirty = Test-RepoDirty -Paths @(
            "backend/app", "backend/tests"
        )
        if ($dirty.Count -gt 0) {
            $script:failures += "backend uncommitted changes after -Fix"
            Write-Host ""
            Write-Host "[FAIL] -Fix modified files that are not committed:" -ForegroundColor Red
            foreach ($f in $dirty) {
                Write-Host "  - $f" -ForegroundColor Red
            }
            Write-Host "Stage and commit these changes, then re-run ./pre-push.ps1" -ForegroundColor Red
        }
    }

    Invoke-Step "backend ruff check" {
        uv run ruff check app/ tests/
    }

    Invoke-Step "backend ruff format" {
        uv run ruff format --check app/ tests/
    }

    Invoke-Step "backend mypy" {
        uv run mypy app/
    }

    Invoke-Step "backend pytest" {
        uv run pytest tests/ -q
    }
} finally {
    Pop-Location
}

if (-not $BackendOnly) {
    # ── Frontend ────────────────────────────────────────────────────
    Write-Host ""
    Write-Host "---- Frontend ----" -ForegroundColor Magenta

    Push-Location (Join-Path $RepoRoot "frontend")
    try {
        Invoke-Step "frontend pnpm lint" {
            pnpm lint
        }

        Invoke-Step "frontend pnpm test" {
            pnpm test
        }

        Invoke-Step "frontend pnpm build" {
            pnpm build
        }
    } finally {
        Pop-Location
    }

    # ── API contract (matches CI `contract` job) ──────────────────
    Write-Host ""
    Write-Host "---- API Contract ----" -ForegroundColor Magenta

    Invoke-Step "contract check" {
        python scripts/check_api_contract.py
        if ($LASTEXITCODE -ne 0 -and (Test-Path "contract-report.txt")) {
            Write-Host ""
            Write-Host "--- contract-report.txt ---" -ForegroundColor Yellow
            Get-Content "contract-report.txt" | Write-Host
        }
    }

    Invoke-Step "contract check unit tests" {
        Push-Location (Join-Path $RepoRoot "backend")
        try {
            uv run python -m pytest ../scripts/tests/ -v --tb=short
        } finally {
            Pop-Location
        }
    }
}

# ── Summary ─────────────────────────────────────────────────────
Write-Host ""
if ($script:failures.Count -gt 0) {
    Write-Host "=== Checks FAILED ===" -ForegroundColor Red
    Write-Host "Failed steps:" -ForegroundColor Red
    foreach ($f in $script:failures) {
        Write-Host "  - $f" -ForegroundColor Red
    }
    if ($script:warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "Warnings (not blocking):" -ForegroundColor Yellow
        foreach ($w in $script:warnings) {
            Write-Host "  - $w" -ForegroundColor Yellow
        }
    }
    Write-Host ""
    Write-Host "DO NOT push. Fix the failures above and re-run:" -ForegroundColor Red
    Write-Host "  ./pre-push.ps1" -ForegroundColor Red
    if (-not $Fix) {
        Write-Host "  ./pre-push.ps1 -Fix   # auto-fix ruff issues, then re-check" -ForegroundColor DarkGray
    }
    exit 1
}

Write-Host "=== All checks passed! Ready to push ===" -ForegroundColor Green
if ($script:warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "Warnings (not blocking):" -ForegroundColor Yellow
    foreach ($w in $script:warnings) {
        Write-Host "  - $w" -ForegroundColor Yellow
    }
}
exit 0
