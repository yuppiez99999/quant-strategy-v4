<#
.SYNOPSIS
    量化策略系统 v5.10 — 一键部署到 GitHub 脚本
.DESCRIPTION
    自动完成代码整理、敏感文件检查、Git 提交和推送到 GitHub
.NOTES
    作者: Quant Strategy Team
    版本: 1.0
    日期: 2026-07-02
#>

$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  量化策略系统 v5.10 — 一键部署到 GitHub" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# ============================================================
# 1. 检查 Git 是否安装
# ============================================================
Write-Host "`n[1/6] 检查 Git 环境..." -ForegroundColor Yellow
try {
    $gitVersion = git --version 2>&1
    Write-Host "  ✅ Git 已安装: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Git 未安装，请先安装 Git: https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

# ============================================================
# 2. 检查 .gitignore 是否正确配置
# ============================================================
Write-Host "`n[2/6] 检查 .gitignore 配置..." -ForegroundColor Yellow
$gitignorePath = ".gitignore"
if (Test-Path $gitignorePath) {
    $gitignoreContent = Get-Content $gitignorePath -Raw
    $requiredPatterns = @(".env", "config/positions.json", "models/", "*.pth", "*.bin")
    foreach ($pattern in $requiredPatterns) {
        if ($gitignoreContent -notmatch [regex]::Escape($pattern)) {
            Write-Host "  ⚠️  .gitignore 缺少规则: $pattern" -ForegroundColor Yellow
        } else {
            Write-Host "  ✅ .gitignore 包含: $pattern" -ForegroundColor Green
        }
    }
} else {
    Write-Host "  ❌ .gitignore 不存在!" -ForegroundColor Red
    exit 1
}

# ============================================================
# 3. 检查敏感文件
# ============================================================
Write-Host "`n[3/6] 检查敏感文件是否在 .gitignore 中..." -ForegroundColor Yellow
$sensitiveFiles = @(
    ".env",
    "config/positions.json",
    "config/price_history.jsonl",
    "data/akshare*.parquet",
    "data/yizhao/*",
    "models/*.pth",
    "models/*.bin",
    "models/*.pkl",
    "*.log"
)

$shouldCommit = $true
foreach ($file in $sensitiveFiles) {
    if (Test-Path $file) {
        $isIgnored = git check-ignore -q $file 2>&1
        if (-not $LASTEXITCODE) {
            Write-Host "  ✅ 敏感文件 $file 已被 .gitignore 忽略" -ForegroundColor Green
        } else {
            Write-Host "  ❌ 敏感文件 $file 未被 .gitignore 忽略!" -ForegroundColor Red
            Write-Host "     请将 $file 添加到 .gitignore 或删除" -ForegroundColor Red
            $shouldCommit = $false
        }
    }
}

if (-not $shouldCommit) {
    Write-Host "`n  ⚠️  存在未被忽略的敏感文件，请修复后重新运行" -ForegroundColor Yellow
    exit 1
}

# ============================================================
# 4. 确认提交信息
# ============================================================
Write-Host "`n[4/6] 确认提交信息..." -ForegroundColor Yellow
$commitMessage = "chore: cross-platform path refactoring for macOS migration"
Write-Host "  提交信息: $commitMessage" -ForegroundColor White

# ============================================================
# 5. Git 操作
# ============================================================
Write-Host "`n[5/6] 执行 Git 操作..." -ForegroundColor Yellow

try {
    Write-Host "  ⏳ git add -A..." -ForegroundColor Gray
    git add -A

    Write-Host "  ⏳ git status..." -ForegroundColor Gray
    git status

    Write-Host "  ⏳ git commit..." -ForegroundColor Gray
    git commit -m $commitMessage

    Write-Host "  ⏳ git push..." -ForegroundColor Gray
    git push

    Write-Host "`n  ✅ Git 推送成功!" -ForegroundColor Green
} catch {
    Write-Host "`n  ❌ Git 操作失败: $_" -ForegroundColor Red
    exit 1
}

# ============================================================
# 6. 后续步骤提示
# ============================================================
Write-Host "`n[6/6] 部署完成!" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "`n在 MacBook 上的后续操作:" -ForegroundColor Yellow
Write-Host "`n1. 安装 Homebrew:" -ForegroundColor White
Write-Host "   /bin/bash -c `"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)`"" -ForegroundColor Gray
Write-Host "`n2. 安装 Python:" -ForegroundColor White
Write-Host "   brew install pyenv" -ForegroundColor Gray
Write-Host "   pyenv install 3.11" -ForegroundColor Gray
Write-Host "   pyenv local 3.11" -ForegroundColor Gray
Write-Host "`n3. 克隆仓库:" -ForegroundColor White
Write-Host "   git clone <你的仓库地址> quant_strategy" -ForegroundColor Gray
Write-Host "`n4. 安装依赖:" -ForegroundColor White
Write-Host "   python -m venv .venv" -ForegroundColor Gray
Write-Host "   source .venv/bin/activate" -ForegroundColor Gray
Write-Host "   pip install -r requirements.txt" -ForegroundColor Gray
Write-Host "`n5. 配置环境变量:" -ForegroundColor White
Write-Host "   cp .env.macOS.example .env" -ForegroundColor Gray
Write-Host "   # 编辑 .env 填入你的 API Key" -ForegroundColor Gray
Write-Host "`n6. 安装中文字体:" -ForegroundColor White
Write-Host "   brew install homebrew/cask-fonts/font-simhei" -ForegroundColor Gray
Write-Host "   brew install homebrew/cask-fonts/font-simsun" -ForegroundColor Gray
Write-Host "`n7. 启动 UI:" -ForegroundColor White
Write-Host "   streamlit run ui/app.py" -ForegroundColor Gray
Write-Host "`n=============================================" -ForegroundColor Cyan