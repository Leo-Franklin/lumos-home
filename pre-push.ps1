#!/usr/bin/env pwsh
# pre-push.ps1 - Git push 前统一检查脚本 (前端 + 后端)
#
# 用法:
#   ./pre-push.ps1              # 检查；可自动修复项失败时会 fix 并重试一次
#   ./pre-push.ps1 -Strict      # 严格镜像 CI，不修改任何文件
#   ./pre-push.ps1 -Fix         # 检查前先主动跑一遍全部 auto-fix，再验证
#   ./pre-push.ps1 -InstallHook # 安装 git pre-push hook，之后每次 push 自动跑本脚本
#
# 默认可自动修复并重试的步骤:
#   - backend ruff check / format
#   - frontend eslint + prettier (pnpm lint:fix)
#
# 若自动修复产生了未提交改动，脚本会失败并列出文件，需先 commit 再 push。
#
# frontend/.prettierrc.json 使用 "endOfLine": "auto"，Windows CRLF 与 Linux LF 均可通过 prettier --check。

[CmdletBinding()]
param(
    [switch]$Fix,
    [switch]$Strict,
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

# 必填环境变量 (后端 pytest 需要，与 ci.yml 一致)
$env:JWT_SECRET_KEY = 'test_secret_key_that_is_at_least_32_characters_long'
$env:ADMIN_PASSWORD = 'testpassword_for_ci_only'
$env:CORS_ALLOW_ORIGINS = 'http://localhost:5173'

$script:failures = @()
$script:warnings = @()
$script:autoFixRan = $false
$script:dirtyReported = $false
$script:autoFixEnabled = -not $Strict

$AutoFixPathPatterns = @(
    '^backend/app/',
    '^backend/tests/',
    '^frontend/'
)

function Test-RepoDirty {
    param([string[]]$PathPatterns = $AutoFixPathPatterns)
    Push-Location $RepoRoot
    try {
        $diff = git diff --name-only 2>$null
        $untracked = git ls-files --others --exclude-standard 2>$null
        $changed = @($diff + $untracked | Where-Object { $_ })
        return @($changed | Where-Object {
                $p = $_
                $PathPatterns | Where-Object { $p -match $_ }
            })
    } finally {
        Pop-Location
    }
}

function Report-DirtyAfterAutoFix {
    param([string]$Reason)
    if ($script:dirtyReported) { return $true }

    $dirty = Test-RepoDirty
    if ($dirty.Count -eq 0) { return $false }

    $script:dirtyReported = $true
    $script:failures += $Reason
    Write-Host ""
    Write-Host "[FAIL] Auto-fix modified files that are not committed:" -ForegroundColor Red
    foreach ($f in $dirty) {
        Write-Host "  - $f" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Review, then stage and commit:" -ForegroundColor Yellow
    Write-Host "  git add -A" -ForegroundColor DarkGray
    Write-Host "  git commit -m `"chore: apply pre-push auto-fix`"" -ForegroundColor DarkGray
    Write-Host "  ./pre-push.ps1" -ForegroundColor DarkGray
    return $true
}

function Invoke-BackendStyleFix {
    Write-Host "  -> running backend ruff --fix + format" -ForegroundColor DarkGray
    uv run ruff check --fix app/ tests/
    if ($LASTEXITCODE -ne 0) { return }
    uv run ruff format app/ tests/
}

function Invoke-FrontendLintFix {
    Write-Host "  -> running frontend pnpm lint:fix" -ForegroundColor DarkGray
    pnpm lint:fix
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
        return $false
    }
    Write-Host "[OK] $Label" -ForegroundColor Green
    return $true
}

function Invoke-FixableStep {
    param(
        [string]$Label,
        [scriptblock]$Check,
        [scriptblock]$Fix
    )
    $ok = Invoke-Step -Label $Label -Action $Check
    if ($ok) { return }

    if (-not $script:autoFixEnabled) {
        Write-Host "  (use -Fix or drop -Strict to auto-repair)" -ForegroundColor DarkGray
        return
    }

    Write-Host "[AUTO-FIX] $Label failed — attempting repair and one retry..." -ForegroundColor Yellow
    $script:autoFixRan = $true
    Push-Location $PWD
    try {
        & $Fix
        $fixExit = $LASTEXITCODE
        if ($null -eq $fixExit) { $fixExit = 0 }
        if ($fixExit -ne 0) {
            Write-Host "[FAIL] Auto-fix command failed (exit=$fixExit)" -ForegroundColor Red
            return
        }
    } finally {
        Pop-Location
    }

    # Remove stale failure entry before retry
    $script:failures = @($script:failures | Where-Object { $_ -ne $Label })
    Write-Host "[RETRY] $Label" -ForegroundColor Cyan
    $null = Invoke-Step -Label $Label -Action $Check
}

Write-Host ""
Write-Host "=== Pre-Push Checks (frontend + backend) ===" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot" -ForegroundColor DarkGray
if ($Strict) {
    Write-Host "Mode: -Strict (CI mirror, no file changes)" -ForegroundColor DarkGray
} elseif ($Fix) {
    Write-Host "Mode: -Fix (proactive auto-fix, then verify)" -ForegroundColor Yellow
} else {
    Write-Host "Mode: verify with auto-retry on fixable failures" -ForegroundColor DarkGray
}

# ── Proactive fix (-Fix) ────────────────────────────────────────
if ($Fix -and $script:autoFixEnabled) {
    Write-Host ""
    Write-Host "---- Proactive Auto-Fix ----" -ForegroundColor Magenta
    $script:autoFixRan = $true

    Push-Location (Join-Path $RepoRoot "backend")
    try {
        Invoke-Step "backend proactive fix" { Invoke-BackendStyleFix }
    } finally {
        Pop-Location
    }

    if (-not $BackendOnly) {
        Push-Location (Join-Path $RepoRoot "frontend")
        try {
            Invoke-Step "frontend proactive fix" { Invoke-FrontendLintFix }
        } finally {
            Pop-Location
        }
    }

    $null = Report-DirtyAfterAutoFix -Reason "uncommitted changes after proactive -Fix"
}

# ── Backend ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "---- Backend ----" -ForegroundColor Magenta

Push-Location (Join-Path $RepoRoot "backend")
try {
    Invoke-FixableStep -Label "backend ruff check" -Check {
        uv run ruff check app/ tests/
    } -Fix {
        Invoke-BackendStyleFix
    }

    Invoke-FixableStep -Label "backend ruff format" -Check {
        uv run ruff format --check app/ tests/
    } -Fix {
        Invoke-BackendStyleFix
    }

    Invoke-Step "backend mypy" {
        uv run mypy app/
    } | Out-Null

    Invoke-Step "backend pytest" {
        uv run pytest tests/ -v --tb=short
    } | Out-Null
} finally {
    Pop-Location
}

if (-not $BackendOnly) {
    # ── Frontend ────────────────────────────────────────────────────
    Write-Host ""
    Write-Host "---- Frontend ----" -ForegroundColor Magenta

    Push-Location (Join-Path $RepoRoot "frontend")
    try {
        Invoke-FixableStep -Label "frontend pnpm lint" -Check {
            pnpm lint
        } -Fix {
            Invoke-FrontendLintFix
        }

        Invoke-Step "frontend pnpm test" {
            pnpm test
        } | Out-Null

        Invoke-Step "frontend pnpm build" {
            pnpm build
        } | Out-Null
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
    } | Out-Null

    Invoke-Step "contract check unit tests" {
        Push-Location (Join-Path $RepoRoot "backend")
        try {
            uv run python -m pytest ../scripts/tests/ -v --tb=short
        } finally {
            Pop-Location
        }
    } | Out-Null
}

# ── Post-check: uncommitted auto-fix edits ──────────────────────
if ($script:autoFixRan) {
    $null = Report-DirtyAfterAutoFix -Reason "uncommitted changes after auto-fix"
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
    if ($Strict) {
        Write-Host "  ./pre-push.ps1 -Fix     # proactive auto-fix before checks" -ForegroundColor DarkGray
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
