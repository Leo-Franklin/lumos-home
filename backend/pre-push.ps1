#!/usr/bin/env pwsh
# pre-push.ps1 - Git push 前检查脚本
# 用法: ./pre-push.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Pre-Push Checks ===" -ForegroundColor Cyan

# 1. 可选：检查未提交的变更（commit 前可跳过）
$skip_uncommitted = $true
$status = git status --porcelain
if (!$skip_uncommitted -and $status) {
    Write-Host "WARNING: 你有未提交的变更:" -ForegroundColor Yellow
    git status --short
    Write-Host "(继续运行其他检查...)" -ForegroundColor Yellow
}

# 2. 运行 ruff format + lint
Write-Host "`n=== Running ruff ===" -ForegroundColor Cyan
uv run ruff format --check .
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ruff format 检查失败" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] ruff format 通过" -ForegroundColor Green

uv run ruff check . --fix
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ruff lint 检查失败" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] ruff lint 通过" -ForegroundColor Green

# 3. 类型检查（mypy）
Write-Host "`n=== Running mypy ===" -ForegroundColor Cyan
uv run mypy app/ --no-error-summary 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: mypy 类型检查失败" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] mypy 通过" -ForegroundColor Green

Write-Host "`n=== All checks passed! Ready to push ===" -ForegroundColor Green