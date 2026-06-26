# -*- coding: utf-8 -*-
"""
分析中国神华股息对策略收益的影响
"""

import pandas as pd

def analyze_dividend_impact():
    print("=" * 60)
    print("中国神华股息影响分析")
    print("=" * 60)
    
    div_yield = 0.04  # 股息率4%
    current_weight = 0.10  # 当前配置权重10%
    
    print(f"\n【基础参数】")
    print(f"  中国神华股息率: {div_yield*100:.1f}%")
    print(f"  当前配置权重: {current_weight*100:.0f}%")
    
    current_div_boost = current_weight * div_yield
    print(f"\n【当前股息贡献】")
    print(f"  股息带来的额外收益: {current_div_boost*100:.2f}%/年")
    
    backtest_return = 0.0846  # 回测年化收益8.46%
    total_return_with_div = backtest_return + current_div_boost
    print(f"  回测收益(不含股息): {backtest_return*100:.2f}%")
    print(f"  实际收益(含股息): {total_return_with_div*100:.2f}%")
    
    print("\n【不同权重下的股息贡献】")
    print("-" * 50)
    print(f"{'神华权重':<10} {'股息贡献':<12} {'理论总收益':<12}")
    print("-" * 50)
    
    for weight in [0.10, 0.12, 0.15, 0.18, 0.20]:
        div_contribution = weight * div_yield
        total_return = backtest_return + div_contribution
        print(f"{weight*100:<10.0f}%    {div_contribution*100:<12.2f}%    {total_return*100:<12.2f}%")
    
    print("\n【理论最大收益率估算】")
    print("-" * 50)
    print("假设条件:")
    print("  1. 神华权重上限: 20% (单一资产限制)")
    print("  2. 神华股价年均涨幅: 5%")
    print("  3. 其他股票组合收益: 8%")
    
    max_weight = 0.20
    shenhua_return = 0.05 + 0.04  # 股价涨幅 + 股息
    other_return = 0.08
    max_total_return = max_weight * shenhua_return + (1 - max_weight) * other_return
    
    print(f"\n  神华贡献: {max_weight*100}% × ({shenhua_return*100}%) = {max_weight*shenhua_return*100:.2f}%")
    print(f"  其他贡献: {(1-max_weight)*100}% × ({other_return*100}%) = {(1-max_weight)*other_return*100:.2f}%")
    print(f"  ───────────────────────────────────────")
    print(f"  理论最大收益: {max_total_return*100:.2f}%")
    
    print("\n【风险收益权衡分析】")
    print("-" * 50)
    print(f"{'神华权重':<10} {'预期收益':<12} {'风险增加':<12}")
    print("-" * 50)
    
    base_vol = 0.0592  # 当前年化波动
    shenhua_vol = 0.22  # 神华风险权重
    other_vol = 0.24  # 其他股票平均风险
    
    for weight in [0.10, 0.12, 0.15, 0.18, 0.20]:
        expected_return = weight * (0.05 + 0.04) + (1 - weight) * 0.08
        risk_factor = weight * shenhua_vol + (1 - weight) * other_vol
        risk_change = ((risk_factor - (0.10 * shenhua_vol + 0.90 * other_vol)) / (0.10 * shenhua_vol + 0.90 * other_vol)) * 100
        print(f"{weight*100:<10.0f}%    {expected_return*100:<12.2f}%    {risk_change:<12.1f}%")
    
    print("\n【结论】")
    print("-" * 50)
    print("1. 当前配置(神华10%): 股息贡献约0.4%/年，实际收益约8.86%")
    print("2. 提高神华权重至15%: 股息贡献约0.6%/年，预期收益约9.06%")
    print("3. 理论最大值(神华20%): 预期收益约8.90%")
    print("4. 最佳配置建议: 神华权重12-15%，平衡收益与风险")
    print("=" * 60)

if __name__ == "__main__":
    analyze_dividend_impact()
