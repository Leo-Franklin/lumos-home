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
$env:PYTHONUNBUFFERED = '1'

$script:failures = @()
$script:warnings = @()
$script:autoFixRan = $false
$script:dirtyReported = $false
$script:autoFixEnabled = -not $Strict
$script:stepIndex = 0
$script:stepTotal = 0

$AutoFixPathPatterns = @(
    '^backend/app/',
    '^backend/tests/',
    '^frontend/'
)

function Get-StepTotal {
    $total = 0
    if ($Fix -and $script:autoFixEnabled) {
        $total += 1
        if (-not $BackendOnly) { $total += 1 }
    }
    $total += 4  # backend: ruff check, ruff format, mypy, pytest
    if (-not $BackendOnly) {
        $total += 5  # frontend lint, test, build + contract check + contract tests
    }
    return $total
}

function Format-Elapsed {
    param([TimeSpan]$Elapsed)
    if ($Elapsed.TotalMinutes -ge 1) {
        return $Elapsed.ToString('mm\:ss')
    }
    return ('{0:F1}s' -f $Elapsed.TotalSeconds)
}

function Convert-PipelineLine {
    param($Item)
    if ($Item -is [System.Management.Automation.ErrorRecord]) {
        if ($Item.ErrorDetails.Message) { return $Item.ErrorDetails.Message }
        if ($Item.Exception.Message) { return $Item.Exception.Message }
    }
    return $Item.ToString()
}

function Write-StepOutput {
    param(
        [string]$Line,
        [System.Collections.Generic.List[string]]$Buffer
    )
    if ($null -ne $Line -and $Line.Length -gt 0) {
        Write-Host $Line
        [void]$Buffer.Add($Line)
    }
}

function Write-FailureOutput {
    param(
        [string]$Label,
        [System.Collections.Generic.List[string]]$OutputLines,
        [int]$TailLines = 80
    )
    if ($OutputLines.Count -eq 0) {
        Write-Host "  (no captured output — command may have failed before printing)" -ForegroundColor DarkGray
        return
    }

    Write-Host ""
    Write-Host "--- Output: $Label ---" -ForegroundColor Red
    if ($OutputLines.Count -gt $TailLines) {
        Write-Host "(showing last $TailLines of $($OutputLines.Count) lines)" -ForegroundColor DarkGray
        $start = $OutputLines.Count - $TailLines
        for ($i = $start; $i -lt $OutputLines.Count; $i++) {
            Write-Host $OutputLines[$i]
        }
    } else {
        foreach ($line in $OutputLines) {
            Write-Host $line
        }
    }
    Write-Host "--- end output ---" -ForegroundColor Red
}

function Invoke-ProcessWithLiveOutput {
    param(
        [string]$Command,
        [string]$WorkingDirectory = $PWD.Path
    )

    $outputLines = [System.Collections.Generic.List[string]]::new()
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $lastHeartbeatAt = [TimeSpan]::Zero

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = 'cmd.exe'
    $psi.Arguments = "/d /s /c $Command"
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    $proc = [System.Diagnostics.Process]::Start($psi)
    if ($null -eq $proc) {
        $sw.Stop()
        return @{
            ExitCode = 1
            Output = $outputLines
            Elapsed = $sw.Elapsed
        }
    }

    $outReader = $proc.StandardOutput
    $errReader = $proc.StandardError

    while (-not $proc.HasExited -or -not $outReader.EndOfStream -or -not $errReader.EndOfStream) {
        $wrote = $false
        while ($outReader.Peek() -ge 0) {
            Write-StepOutput -Line $outReader.ReadLine() -Buffer $outputLines
            $wrote = $true
        }
        while ($errReader.Peek() -ge 0) {
            Write-StepOutput -Line $errReader.ReadLine() -Buffer $outputLines
            $wrote = $true
        }

        if (-not $wrote -and -not $proc.HasExited) {
            $now = $sw.Elapsed
            if (($now - $lastHeartbeatAt).TotalSeconds -ge 8) {
                Write-Host ("  ... still running ({0} elapsed)" -f (Format-Elapsed $now)) -ForegroundColor DarkGray
                $lastHeartbeatAt = $now
            }
            Start-Sleep -Milliseconds 250
        } elseif (-not $proc.HasExited) {
            Start-Sleep -Milliseconds 50
        }
    }

    $proc.WaitForExit()
    $sw.Stop()
    return @{
        ExitCode = $proc.ExitCode
        Output = $outputLines
        Elapsed = $sw.Elapsed
    }
}

function Invoke-CommandWithOutput {
    param(
        [scriptblock]$Action,
        [switch]$LongRunning
    )

    $outputLines = [System.Collections.Generic.List[string]]::new()
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $lastHeartbeatAt = [TimeSpan]::Zero

    & $Action 2>&1 | ForEach-Object {
        if ($LongRunning) {
            $now = $sw.Elapsed
            if (($now - $lastHeartbeatAt).TotalSeconds -ge 8) {
                Write-Host ("  ... still running ({0} elapsed)" -f (Format-Elapsed $now)) -ForegroundColor DarkGray
                $lastHeartbeatAt = $now
            }
        }
        Write-StepOutput -Line (Convert-PipelineLine $_) -Buffer $outputLines
    }

    if ($LongRunning -and $outputLines.Count -eq 0 -and $sw.Elapsed.TotalSeconds -ge 8) {
        Write-Host ("  ... completed with no stdout/stderr ({0} elapsed)" -f (Format-Elapsed $sw.Elapsed)) -ForegroundColor DarkGray
    }

    $sw.Stop()
    $exit = $LASTEXITCODE
    if ($null -eq $exit) { $exit = 0 }

    return @{
        ExitCode = $exit
        Output = $outputLines
        Elapsed = $sw.Elapsed
    }
}

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
    $result = Invoke-CommandWithOutput -Action {
        uv run ruff check --fix app/ tests/
        if ($LASTEXITCODE -ne 0) { return }
        uv run ruff format app/ tests/
    }
    if ($result.ExitCode -ne 0) {
        Write-FailureOutput -Label "backend auto-fix" -OutputLines $result.Output
    }
    return $result.ExitCode
}

function Invoke-FrontendLintFix {
    Write-Host "  -> running frontend pnpm lint:fix" -ForegroundColor DarkGray
    $result = Invoke-CommandWithOutput -Action { pnpm lint:fix }
    if ($result.ExitCode -ne 0) {
        Write-FailureOutput -Label "frontend lint:fix" -OutputLines $result.Output
    }
    return $result.ExitCode
}

function Invoke-Step {
    param(
        [string]$Label,
        [scriptblock]$Action,
        [string]$Command = "",
        [string]$WorkingDirectory = "",
        [switch]$WarnOnly,
        [switch]$LongRunning
    )

    $script:stepIndex++
    $progress = "[$script:stepIndex/$script:stepTotal]"

    Write-Host ""
    Write-Host "$progress $Label" -ForegroundColor Cyan
    if ($Command) {
        Write-Host "  cmd: $Command" -ForegroundColor DarkGray
    }
    if ($LongRunning) {
        Write-Host "  started $(Get-Date -Format 'HH:mm:ss') (long-running — output streams below)" -ForegroundColor DarkGray
    }

    if ($LongRunning -and $Command) {
        $workDir = if ($WorkingDirectory) { $WorkingDirectory } else { $PWD.Path }
        $result = Invoke-ProcessWithLiveOutput -Command $Command -WorkingDirectory $workDir
    } else {
        $result = Invoke-CommandWithOutput -Action $Action -LongRunning:$LongRunning
    }
    $elapsed = Format-Elapsed $result.Elapsed

    if ($result.ExitCode -ne 0) {
        if ($result.Output.Count -eq 0) {
            Write-FailureOutput -Label $Label -OutputLines $result.Output
        } else {
            Write-Host "  See output above, or the tail below if the log is long." -ForegroundColor DarkGray
            if ($result.Output.Count -gt 40) {
                Write-FailureOutput -Label $Label -OutputLines $result.Output -TailLines 40
            }
        }
        if ($WarnOnly) {
            $script:warnings += $Label
            Write-Host "[WARN] $Label (exit=$($result.ExitCode), $elapsed)" -ForegroundColor Yellow
        } else {
            $script:failures += $Label
            Write-Host "[FAIL] $Label (exit=$($result.ExitCode), $elapsed)" -ForegroundColor Red
        }
        return $false
    }

    Write-Host "[OK] $Label ($elapsed)" -ForegroundColor Green
    return $true
}

function Invoke-FixableStep {
    param(
        [string]$Label,
        [scriptblock]$Check,
        [string]$CheckCommand = "",
        [scriptblock]$Fix,
        [switch]$LongRunning
    )

    $ok = Invoke-Step -Label $Label -Action $Check -Command $CheckCommand -LongRunning:$LongRunning
    if ($ok) { return }

    if (-not $script:autoFixEnabled) {
        Write-Host "  (use -Fix or drop -Strict to auto-repair)" -ForegroundColor DarkGray
        return
    }

    Write-Host "[AUTO-FIX] $Label failed — attempting repair and one retry..." -ForegroundColor Yellow
    $script:autoFixRan = $true
    Push-Location $PWD
    try {
        $fixExit = & $Fix
        if ($null -eq $fixExit) { $fixExit = $LASTEXITCODE }
        if ($null -eq $fixExit) { $fixExit = 0 }
        if ($fixExit -ne 0) {
            Write-Host "[FAIL] Auto-fix command failed (exit=$fixExit)" -ForegroundColor Red
            return
        }
    } finally {
        Pop-Location
    }

    $script:failures = @($script:failures | Where-Object { $_ -ne $Label })
    Write-Host "[RETRY] $Label" -ForegroundColor Cyan
    $null = Invoke-Step -Label $Label -Action $Check -Command $CheckCommand -LongRunning:$LongRunning
}

$script:stepTotal = Get-StepTotal

Write-Host ""
Write-Host "=== Pre-Push Checks (frontend + backend) ===" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot" -ForegroundColor DarkGray
Write-Host "Steps: $script:stepTotal" -ForegroundColor DarkGray
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
        Invoke-Step -Label "backend proactive fix" -Command "uv run ruff check --fix + ruff format" -Action {
            $code = Invoke-BackendStyleFix
            if ($code -ne 0) { exit $code }
        }
    } finally {
        Pop-Location
    }

    if (-not $BackendOnly) {
        Push-Location (Join-Path $RepoRoot "frontend")
        try {
            Invoke-Step -Label "frontend proactive fix" -Command "pnpm lint:fix" -Action {
                $code = Invoke-FrontendLintFix
                if ($code -ne 0) { exit $code }
            }
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
    Invoke-FixableStep -Label "backend ruff check" -CheckCommand "uv run ruff check app/ tests/" -Check {
        uv run ruff check app/ tests/
    } -Fix {
        Invoke-BackendStyleFix
    }

    Invoke-FixableStep -Label "backend ruff format" -CheckCommand "uv run ruff format --check app/ tests/" -Check {
        uv run ruff format --check app/ tests/
    } -Fix {
        Invoke-BackendStyleFix
    }

    Invoke-Step -Label "backend mypy" -Command "uv run mypy app/" -LongRunning -Action {
        uv run mypy app/
    } | Out-Null

    Invoke-Step -Label "backend pytest" -Command "uv run pytest tests/ -v --tb=short" -LongRunning -Action {
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
        Invoke-FixableStep -Label "frontend pnpm lint" -CheckCommand "pnpm lint" -Check {
            pnpm lint
        } -Fix {
            Invoke-FrontendLintFix
        }

        Invoke-Step -Label "frontend pnpm test" -Command "pnpm test" -LongRunning -Action {
            pnpm test
        } | Out-Null

        Invoke-Step -Label "frontend pnpm build" -Command "pnpm build" -LongRunning -Action {
            pnpm build
        } | Out-Null
    } finally {
        Pop-Location
    }

    # ── API contract (matches CI `contract` job) ──────────────────
    Write-Host ""
    Write-Host "---- API Contract ----" -ForegroundColor Magenta

    Invoke-Step -Label "contract check" -Command "python scripts/check_api_contract.py" -Action {
        python scripts/check_api_contract.py
        if ($LASTEXITCODE -ne 0 -and (Test-Path "contract-report.txt")) {
            Write-Host ""
            Write-Host "--- contract-report.txt ---" -ForegroundColor Yellow
            Get-Content "contract-report.txt" | Write-Host
        }
    } | Out-Null

    Invoke-Step -Label "contract check unit tests" `
        -Command "uv run python -m pytest ../scripts/tests/ -v --tb=short" `
        -WorkingDirectory (Join-Path $RepoRoot "backend") `
        -LongRunning `
        -Action {
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
    Write-Host "Scroll up for '--- Output: <step> ---' blocks with full error details." -ForegroundColor Yellow
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
