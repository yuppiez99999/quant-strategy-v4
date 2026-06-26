# -*- coding: utf-8 -*-
"""中际旭创减仓再平衡计算"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

current_price = 1154.99
current_shares = 600
current_value = current_shares * current_price
total_asset = 1000000.0
current_weight = current_value / total_asset
target_weight = 0.15
target_value = total_asset * target_weight

print("=" * 60)
print("  中际旭创(300308) 减仓再平衡方案")
print("=" * 60)
print(f"  当前持仓: {current_shares}股 x {current_price:.2f} = {current_value:,.2f}")
print(f"  当前权重: {current_weight*100:.1f}% (目标 15%)")
print(f"  需减仓:   {current_value - target_value:,.2f}")
print()

excess = current_value - target_value
excess_shares = int(excess / current_price / 100) * 100
sell_value = excess_shares * current_price
new_shares = current_shares - excess_shares
new_value = new_shares * current_price
new_weight = new_value / total_asset

print(f"  建议卖出: {excess_shares}股 = {sell_value:,.2f}")
print(f"  减仓后:   {new_shares}股 x {current_price:.2f} = {new_value:,.2f}")
print(f"  减仓后权重: {new_weight*100:.1f}%")
print(f"  回笼资金:   {sell_value:,.2f}")
print()

# 资金再分配
print("=" * 60)
print("  回笼资金再分配方案 (总额 {:,})".format(int(sell_value)))
print("=" * 60)

targets = [
    ("北方华创", "002371", 585.74, 0.15, 76146, "高风险 -15%"),
    ("中芯国际", "688981", 121.92, 0.10, 7315, "高风险 -15%"),
    ("海光信息", "688041", 259.70, 0.12, 64925, "高风险 -15%"),
    ("恒瑞医药", "600276", 45.94, 0.12, 78098, "中风险 -15%"),
    ("浪潮信息", "000977", 57.89, 0.08, 46312, "中风险 -15%"),
    ("华安黄金ETF", "518880", 8.95, 0.16, 96692, "低风险 -8%"),
]

total_needed = 0
allocations = []
for name, code, price, tw, cv, risk in targets:
    target_v = total_asset * tw
    gap = target_v - cv
    if gap > 0:
        shares = int(gap / price / 100) * 100
        cost = shares * price
        total_needed += cost
        allocations.append((name, code, price, shares, cost, tw, risk))

for name, code, price, shares, cost, tw, risk in allocations:
    pct = cost / sell_value * 100
    print(f"  {name:8s} {code}  +{shares:5d}股  {cost:>12,.2f} ({pct:5.1f}%)  补至 {tw*100:.0f}%  [{risk}]")

print(f"\n  资金需求: {total_needed:,.2f}")
print(f"  回笼资金: {sell_value:,.2f}")
print(f"  差额:     {sell_value - total_needed:,.2f}")

# 执行摘要
print()
print("=" * 60)
print("  执行摘要")
print("=" * 60)
print(f"  卖出: 中际旭创 {excess_shares}股  回笼 {sell_value:,.2f}")
print(f"  买入: 6只低配标的  投入 {total_needed:,.2f}")
print(f"  剩余现金: {sell_value - total_needed:,.2f}")
print()
print("  建议在 9:30 开盘后分批执行，避免冲击成本")