# -*- coding: utf-8 -*-
"""
量化策略系统 - GitHub 上传准备脚本
检查并清理敏感文件，确保代码库安全
"""

import os
import shutil
from pathlib import Path

# 当前目录
BASE_DIR = Path(__file__).parent

# 敏感文件/目录列表（即使有 .gitignore 也要额外检查）
SENSITIVE_FILES = [
    # 配置文件
    "config/positions.json",
    "config/price_history.jsonl",
    "config/settings.yaml",
    "config/portfolio.yaml",
    "config/watchlist.yaml",
    "config/rebalance.yaml",
    "config/risk.yaml",
    
    # 数据文件
    "investment_report.json",
    "investment_report.md",
    "build_plan_100w.json",
    "build_plan_100w.md",
    "training_data.csv",
    
    # 日志和报告
    "daily_report.txt",
    "rebalance_output.txt",
    "help_output.txt",
    "test_output.txt",
    
    # 临时文件
    "_quick_test.py",
    "_test_models.py",
    "test_*.py",
    "verify_*.py",
    "update_*.py",
    "diagnose_*.py",
    "predict_2027.py",
    
    # 批处理文件
    "*.bat",
    "*.ps1",
    
    # 其他
    "requirements.txt",  # 可能包含内部依赖
]

# 需要备份的目录
BACKUP_DIRS = [
    "Shadowbroker/",
    "_archive_20260620/",
    "data/",
    "models/",
    "modes/",
    "logs/",
]

def check_gitignore():
    """检查 .gitignore 是否存在"""
    gitignore = BASE_DIR / ".gitignore"
    if gitignore.exists():
        print("[OK] .gitignore 文件存在")
        return True
    else:
        print("[FAIL] .gitignore 文件不存在！")
        return False

def list_tracked_files():
    """列出 git 跟踪的文件"""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        files = result.stdout.strip().split('\n')
        return [f for f in files if f]
    except Exception as e:
        print("[WARN] 无法执行 git 命令: {}".format(e))
        return []

def check_sensitive_in_git(tracked_files):
    """检查敏感文件是否在 git 跟踪中"""
    sensitive_found = []
    for pattern in SENSITIVE_FILES:
        if '*' in pattern:
            # 通配符匹配
            import fnmatch
            for f in tracked_files:
                if fnmatch.fnmatch(os.path.basename(f), pattern):
                    sensitive_found.append(f)
        else:
            if pattern in tracked_files:
                sensitive_found.append(pattern)
    
    return sensitive_found

def create_template_files():
    """创建模板文件供参考"""
    templates = {
        "config/positions_template.json": """{
  "positions": {
    "EXAMPLE": {
      "shares": 10000,
      "avg_cost": 10.00,
      "category": "core_etf",
      "target_weight": 0.10,
      "name": "示例标的"
    }
  },
  "cash": 1000000.00,
  "total_value": 10000000.00,
  "prices": {}
}""",
        "config/portfolio_template.yaml": """# 量化策略系统 - 投资组合配置模板
# 复制此文件为 portfolio.yaml 并填入真实配置

global:
  capital:
    total: 1000000
    equity_portfolio: 700000
    low_risk_portfolio: 300000
  targets:
    annual_return: 0.08
    max_drawdown: 0.08

categories:
  core_etf:
    weight: 0.20
    risk_level: low
  tech_growth:
    weight: 0.30
    risk_level: high
""",
        ".env.template": """# 量化策略系统 - 环境变量模板
# 复制此文件为 .env 并填入真实密钥

# Wind API Key
WIND_API_KEY=your_wind_api_key_here

# AKShare (无需密钥)
# 直接使用

# 其他 API Keys
VOLCENGINE_API_KEY=your_volcengine_key_here
""",
    }
    
    for filepath, content in templates.items():
        full_path = BASE_DIR / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("[OK] 创建模板: {}".format(filepath))

def main():
    print("=" * 60)
    print("量化策略系统 - GitHub 上传准备")
    print("=" * 60)
    
    # 1. 检查 .gitignore
    print("\n[1/4] 检查 .gitignore...")
    if not check_gitignore():
        print("[FAIL] 请先创建 .gitignore 文件！")
        return
    
    # 2. 列出跟踪的文件
    print("\n[2/4] 检查 git 跟踪的文件...")
    tracked_files = list_tracked_files()
    print("[OK] 当前 git 跟踪 {} 个文件".format(len(tracked_files)))
    
    # 3. 检查敏感文件
    print("\n[3/4] 检查敏感文件...")
    sensitive_in_git = check_sensitive_in_git(tracked_files)
    if sensitive_in_git:
        print("[WARN] 发现 {} 个敏感文件在 git 跟踪中:".format(len(sensitive_in_git)))
        for f in sensitive_in_git:
            print("  - {}".format(f))
        print("\n建议操作:")
        print("  1. 从 git 中移除: git rm --cached <file>")
        print("  2. 备份后删除本地文件")
    else:
        print("[OK] 未发现敏感文件在 git 跟踪中")
    
    # 4. 创建模板文件
    print("\n[4/4] 创建模板文件...")
    create_template_files()
    
    print("\n" + "=" * 60)
    print("准备完成！")
    print("=" * 60)
    print("\n下一步操作:")
    print("  1. 检查上述输出是否有敏感文件")
    print("  2. 如有敏感文件，运行: git rm --cached <file>")
    print("  3. 提交更改: git add . && git commit -m 'cleanup for github'")
    print("  4. 推送到 GitHub: git push origin main")
    print("\n模板文件已创建:")
    print("  - config/positions_template.json")
    print("  - config/portfolio_template.yaml")
    print("  - .env.template")
    print("\n协作者需要:")
    print("  1. 复制 positions_template.json -> positions.json")
    print("  2. 复制 portfolio_template.yaml -> portfolio.yaml")
    print("  3. 复制 .env.template -> .env 并填入密钥")

if __name__ == "__main__":
    main()
