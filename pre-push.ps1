#!/usr/bin/env pwsh
# pre-push.ps1 - Git push 前统一检查脚本 (前端 + 后端)
#
# 用法:
#   ./pre-push.ps1
#
# 按 CI workflow 顺序执行所有检查,确保本地通过则线上也通过。
# 后端步骤风格参考 backend/pre-push.ps1;前端步骤对应 ci.yml 的 frontend job。
# 任何一步失败,exit 1;全部通过则打印"Ready to push"。
#
# 已知问题 (Windows + PowerShell only):
#   pnpm lint (即 prettier --check .) 在 Windows PowerShell 下会报告 172 个
#   false positive,但在 Linux/Git Bash 下正常。CI 跑在 ubuntu-latest,不受影响。
#   因此 frontend lint 步骤在本地为 WARN (打印结果但不阻塞),其他步骤为硬 gate。
#   真 gate 看 CI。

$ErrorActionPreference = "Stop"

# 必填环境变量 (后端 pytest 需要)
$env:JWT_SECRET_KEY = 'test_secret_key_that_is_at_least_32_characters_long'
$env:ADMIN_PASSWORD = 'testpassword_for_ci_only'
$env:CORS_ALLOW_ORIGINS = 'http://localhost:5173'

$script:failures = @()
$script:warnings = @()

Write-Host ""
Write-Host "=== Pre-Push Checks (frontend + backend) ===" -ForegroundColor Cyan

# ── Backend ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "---- Backend ----" -ForegroundColor Magenta

Push-Location backend
try {
    # 0. 自动修复 (先 lint fix + format,确保最后一次操作是干净的格式化)
    Write-Host "`n[0/7 auto-fix (ruff)]" -ForegroundColor Cyan
    uv run ruff check --fix app/ tests/
    uv run ruff format app/ tests/
    Write-Host "[OK] auto-fix" -ForegroundColor Green

    # 1. ruff check (匹配 ci.yml backend job: uv run ruff check app/ tests/)
    Write-Host "`n[1/7 ruff check]" -ForegroundColor Cyan
    uv run ruff check app/ tests/
    if ($LASTEXITCODE -ne 0) {
        $script:failures += "1/7 ruff check"
        Write-Host "[FAIL] ruff check (exit=$LASTEXITCODE)" -ForegroundColor Red
    } else {
        Write-Host "[OK] ruff check" -ForegroundColor Green
    }

    # 2. ruff format check (匹配 ci.yml: uv run ruff format --check app/ tests/)
    Write-Host "`n[2/7 ruff format]" -ForegroundColor Cyan
    uv run ruff format --check app/ tests/
    if ($LASTEXITCODE -ne 0) {
        $script:failures += "2/7 ruff format"
        Write-Host "[FAIL] ruff format (exit=$LASTEXITCODE)" -ForegroundColor Red
    } else {
        Write-Host "[OK] ruff format" -ForegroundColor Green
    }

    # 3. mypy (匹配 ci.yml: uv run mypy app/)
    Write-Host "`n[3/7 mypy]" -ForegroundColor Cyan
    uv run mypy app/
    if ($LASTEXITCODE -ne 0) {
        $script:failures += "3/7 mypy"
        Write-Host "[FAIL] mypy (exit=$LASTEXITCODE)" -ForegroundColor Red
    } else {
        Write-Host "[OK] mypy" -ForegroundColor Green
    }

    # 4. pytest (匹配 ci.yml: uv run pytest tests/)
    Write-Host "`n[4/7 pytest]" -ForegroundColor Cyan
    uv run pytest tests/ -q
    if ($LASTEXITCODE -ne 0) {
        $script:failures += "4/7 pytest"
        Write-Host "[FAIL] pytest (exit=$LASTEXITCODE)" -ForegroundColor Red
    } else {
        Write-Host "[OK] pytest" -ForegroundColor Green
    }
} finally {
    Pop-Location
}

# ── Frontend ────────────────────────────────────────────────────
Write-Host ""
Write-Host "---- Frontend ----" -ForegroundColor Magenta

Push-Location frontend
try {
    # 5. pnpm lint (匹配 ci.yml: pnpm lint = eslint . + prettier --check .)
    # Windows PowerShell 下 prettier 会出 172 个 false positive,见头部说明
    Write-Host "`n[5/7 pnpm lint] (WARN only on Windows; CI is the real gate)" -ForegroundColor Cyan
    pnpm lint
    if ($LASTEXITCODE -ne 0) {
        $script:warnings += "5/7 pnpm lint"
        Write-Host "[WARN] pnpm lint failed locally (likely Windows prettier false positive); CI is the real gate" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] pnpm lint" -ForegroundColor Green
    }

    # 6. pnpm test (匹配 ci.yml: pnpm test)
    Write-Host "`n[6/7 pnpm test]" -ForegroundColor Cyan
    pnpm test
    if ($LASTEXITCODE -ne 0) {
        $script:failures += "6/7 pnpm test"
        Write-Host "[FAIL] pnpm test (exit=$LASTEXITCODE)" -ForegroundColor Red
    } else {
        Write-Host "[OK] pnpm test" -ForegroundColor Green
    }

    # 7. pnpm build (匹配 ci.yml: pnpm build)
    Write-Host "`n[7/7 pnpm build]" -ForegroundColor Cyan
    pnpm build
    if ($LASTEXITCODE -ne 0) {
        $script:failures += "7/7 pnpm build"
        Write-Host "[FAIL] pnpm build (exit=$LASTEXITCODE)" -ForegroundColor Red
    } else {
        Write-Host "[OK] pnpm build" -ForegroundColor Green
    }
} finally {
    Pop-Location
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
    Write-Host "DO NOT push. Fix the failures above and re-run." -ForegroundColor Red
    exit 1
}

Write-Host "=== All checks passed! Ready to push ===" -ForegroundColor Green
if ($script:warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "Warnings (not blocking):" -ForegroundColor Yellow
    foreach ($w in $script:warnings) {
        Write-Host "  - $w" -ForegroundColor Yellow
    }
    Write-Host "(CI will re-check these on Linux and is the real gate.)" -ForegroundColor Yellow
}
exit 0
