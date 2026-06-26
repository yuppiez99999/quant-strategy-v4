# -*- coding: utf-8 -*-
"""
量化策略系统 - 从 Git 中移除敏感文件
此脚本会从 git 跟踪中移除敏感文件，但保留本地文件
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

# 需要从 git 中移除的敏感文件
SENSITIVE_FILES = [
    # 配置文件（含策略和风险信息）
    "config/rebalance.yaml",
    "config/risk.yaml",
    
    # 投资报告（含持仓和交易信号）
    "investment_report.json",
    "investment_report.md",
    
    # 测试文件
    "_quick_test.py",
    "_test_models.py",
    "test_decision_engine.py",
    "test_full_report.py",
    "test_glm5.py",
    "test_stop_loss.py",
    
    # 批处理文件（可能含敏感路径）
    "_start_live.bat",
    "close_report.bat",
    "install_close_report_task.bat",
    "install_task.bat",
    "manage_task.bat",
    "run_rebalance.bat",
    "run_report.bat",
    "start_futures_ai_trader.bat",
    "test_task.bat",
    
    # PowerShell 脚本
    "setup_simple.ps1",
    "setup_task.ps1",
    
    # 依赖文件（可能暴露内部包结构）
    "requirements.txt",
]

def remove_from_git(filename):
    """从 git 跟踪中移除文件（保留本地）"""
    try:
        result = subprocess.run(
            ["git", "rm", "--cached", filename],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        if result.returncode == 0:
            print("[OK] 已从 git 移除: {}".format(filename))
            return True
        else:
            # 如果文件不存在于 git 中，忽略错误
            if "did not match" in result.stderr or "did not match" in result.stdout:
                print("[SKIP] 未在 git 中: {}".format(filename))
                return True
            else:
                print("[FAIL] 移除失败: {}".format(filename))
                print("  stderr: {}".format(result.stderr))
                return False
    except Exception as e:
        print("[FAIL] 异常: {} - {}".format(filename, e))
        return False

def main():
    print("=" * 60)
    print("从 Git 中移除敏感文件")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    print("\n开始移除 {} 个敏感文件...\n".format(len(SENSITIVE_FILES)))
    
    for filename in SENSITIVE_FILES:
        if remove_from_git(filename):
            success_count += 1
        else:
            fail_count += 1
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)
    print("成功: {} 个".format(success_count))
    print("失败: {} 个".format(fail_count))
    
    if success_count > 0:
        print("\n下一步操作:")
        print("  1. 检查状态: git status")
        print("  2. 提交更改: git commit -m 'cleanup: remove sensitive files from git'")
        print("  3. 推送到 GitHub: git push origin main")
        print("\n注意:")
        print("  - 本地文件仍然保留，不会被删除")
        print("  - 如需恢复文件，运行: git checkout HEAD -- <filename>")

if __name__ == "__main__":
    main()
