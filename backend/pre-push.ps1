#!/usr/bin/env pwsh
# pre-push.ps1 - Git push 前检查脚本
# 用法: ./pre-push.ps1
# 按 CI workflow 顺序执行所有检查，确保本地通过则线上也通过

$ErrorActionPreference = "Stop"

Write-Host "=== Pre-Push Checks ===" -ForegroundColor Cyan

# 0. 自动修复 (先格式化 + 自动 fix，避免检查阶段才发现可自动修复的问题)
Write-Host "`n[0/5] Auto-fixing..." -ForegroundColor Cyan
uv run ruff format app/ tests/
uv run ruff check --fix app/ tests/
Write-Host "[OK] 自动修复完成" -ForegroundColor Green

# 1. ruff check (匹配 CI lint job: ruff check app/ tests/)
Write-Host "`n[1/5] Running ruff check..." -ForegroundColor Cyan
uv run ruff check app/ tests/
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ruff check 失败" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] ruff check 通过" -ForegroundColor Green

# 2. ruff format check (匹配 CI lint job: ruff format --check app/ tests/)
Write-Host "`n[2/5] Running ruff format check..." -ForegroundColor Cyan
uv run ruff format --check app/ tests/
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ruff format check 失败" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] ruff format 通过" -ForegroundColor Green

# 3. mypy 类型检查 (匹配 CI typecheck job: mypy app/)
Write-Host "`n[3/5] Running mypy..." -ForegroundColor Cyan
uv run mypy app/
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: mypy 类型检查失败" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] mypy 通过" -ForegroundColor Green

# 4. pytest 测试 (匹配 CI test job: pytest tests/ -v)
Write-Host "`n[4/5] Running pytest..." -ForegroundColor Cyan
uv run pytest tests/ -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pytest 测试失败" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] pytest 通过" -ForegroundColor Green

Write-Host "`n=== All checks passed! Ready to push ===" -ForegroundColor Green
