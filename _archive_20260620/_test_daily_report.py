# -*- coding: utf-8 -*-
"""快速测试 daily_report.py 的依赖和核心功能"""

import sys
import os
import time
import io

# Windows 编码修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("  测试 daily_report.py 依赖项")
print("=" * 70)

# 1. 基础库
print("\n[1/5] 基础库测试...")
try:
    import yaml
    import json
    from datetime import datetime
    print("  ✅ yaml, json, datetime: OK")
except Exception as e:
    print(f"  ❌ 错误: {e}")
    sys.exit(1)

# 2. wind_data_provider
print("\n[2/5] wind_data_provider 测试...")
try:
    from wind_data_provider import get_quotes_batch, reset_stats
    print("  ✅ 导入成功")
    # 测试获取行情
    start = time.time()
    test_codes = ["600519.SH", "000858.SZ", "300750.SZ"]
    result = get_quotes_batch(test_codes)
    elapsed = time.time() - start
    print(f"  ✅ 获取 {len(result)} 个标的, 耗时 {elapsed:.1f}s")
    for code, info in list(result.items())[:2]:
        price = info.get("current_price", "N/A")
        source = info.get("source", "unknown")
        print(f"     {code}: price={price}, source={source}")
except Exception as e:
    print(f"  ❌ 错误: {e}")
    import traceback
    traceback.print_exc()

# 3. ai_analysis_enhanced
print("\n[3/5] ai_analysis_enhanced 测试...")
try:
    from ai_analysis_enhanced import EnhancedNewsAnalyzer
    print("  ✅ 导入成功")
except Exception as e:
    print(f"  ⚠️  导入失败 (可选): {e}")

# 4. 配置文件
print("\n[4/5] 配置文件测试...")
portfolio_file = os.path.join(os.path.dirname(__file__), 'config', 'portfolio.yaml')
if os.path.exists(portfolio_file):
    with open(portfolio_file, 'r', encoding='utf-8') as f:
        portfolio = yaml.safe_load(f)
    holdings = portfolio.get('holdings', []) if isinstance(portfolio, dict) else []
    print(f"  ✅ portfolio.yaml 存在, 包含 {len(holdings)} 个持仓")
    for h in list(holdings)[:3]:
        print(f"     {h.get('code', '?')}: {h.get('name', '?')}, {h.get('shares', 0)}股")
else:
    print(f"  ❌ portfolio.yaml 不存在: {portfolio_file}")

# 5. 直接调用 generate_daily_report (带 timeout)
print("\n[5/5] 直接调用 generate_daily_report...")
try:
    from daily_report import generate_daily_report
    print("  开始生成报告（最多等待 60 秒）...")
    start = time.time()
    report = generate_daily_report(enable_ai_analysis=False)  # 先关闭 AI 加速
    elapsed = time.time() - start
    if report:
        print(f"  ✅ 报告生成成功, 长度 {len(report)} 字符, 耗时 {elapsed:.1f}s")
        # 显示报告前几行
        lines = report.split('\n')[:20]
        print("\n  --- 报告预览 ---")
        for line in lines:
            print(f"  {line}")
    else:
        print(f"  ⚠️  报告为空, 耗时 {elapsed:.1f}s")
except Exception as e:
    print(f"  ❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("  测试完成！")
print("=" * 70)
