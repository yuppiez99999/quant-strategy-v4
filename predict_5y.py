# -*- coding: utf-8 -*-
"""v5.2 五年预测 — 基于历史回测 + Monte Carlo"""
import numpy as np
import csv

INITIAL = 3_000_000
YEARS = 5

# 读取 minimax 回测结果（时间最长，2016-至今）
values = []
with open(r'e:\各种PY程序\11_量化策略\data\cache\minimax_backtest_results.csv', 'r') as f:
    r = csv.DictReader(f)
    for row in r:
        values.append(float(row['portfolio_value']))

returns = []
for i in range(1, len(values)):
    if values[i-1] > 0:
        returns.append(values[i] / values[i-1] - 1)

daily_ret = np.array(returns)
annual_ret = np.mean(daily_ret) * 252
annual_vol = np.std(daily_ret) * np.sqrt(252)

peak = np.maximum.accumulate(values)
dds = (peak - np.array(values)) / peak
max_dd = float(np.max(dds))

# 年度
n_years = len(values) / 252
years_list = []
for y in range(int(n_years)):
    s = int(y * 252)
    e = min(int((y+1) * 252), len(values))
    if e > s:
        yr = (values[e-1] / values[s] - 1)
        years_list.append(yr)

# 蒙特卡洛
np.random.seed(42)
N = 10000
mc_final = []
mc_maxdd = []
T = int(YEARS * 252)

for _ in range(N):
    v = INITIAL
    peak_v = INITIAL
    worst_dd = 0
    for _ in range(T):
        d_ret = np.random.normal(annual_ret/252, annual_vol/np.sqrt(252))
        v *= (1 + d_ret)
        if v > peak_v: peak_v = v
        dd = (peak_v - v) / peak_v
        if dd > worst_dd: worst_dd = dd
    mc_final.append(v)
    mc_maxdd.append(worst_dd)

mc_final.sort()
mc_maxdd.sort()

def pct(arr, q):
    return arr[int(len(arr) * q/100)]

print("="*60)
print("v5.2 五年预测（基于 2016-2026 历史回测 + Monte Carlo）")
print("="*60)
print(f"历史数据: {len(values)} 日, {n_years:.1f} 年")
print(f"历史年化收益: {annual_ret*100:+.2f}%")
print(f"历史年化波动: {annual_vol*100:.2f}%")
print(f"历史最大回撤: {max_dd*100:.2f}%")
print()

if years_list:
    print("历史年度收益:")
    for i, yr in enumerate(years_list):
        print(f"  第{i+1}年: {yr*100:+.2f}%")

print(f"\n目标达成（基于历史真实数据）:")
print(f"  年化>=8%: {'OK' if annual_ret>=0.08 else 'FAIL'} ({annual_ret*100:.2f}%)")
print(f"  回撤<=15%: {'OK' if max_dd<=0.15 else 'FAIL'} ({max_dd*100:.2f}%)")

print(f"\n五年后净值预测 (Monte Carlo {N}次):")
print(f"  悲观 (5%):  {pct(mc_final,5):,.0f}  年化 {((pct(mc_final,5)/INITIAL)**(1/YEARS)-1)*100:+.2f}%")
print(f"  保守 (25%): {pct(mc_final,25):,.0f}  年化 {((pct(mc_final,25)/INITIAL)**(1/YEARS)-1)*100:+.2f}%")
print(f"  中位 (50%): {pct(mc_final,50):,.0f}  年化 {((pct(mc_final,50)/INITIAL)**(1/YEARS)-1)*100:+.2f}%")
print(f"  乐观 (75%): {pct(mc_final,75):,.0f}  年化 {((pct(mc_final,75)/INITIAL)**(1/YEARS)-1)*100:+.2f}%")
print(f"  极乐观 (95%): {pct(mc_final,95):,.0f}  年化 {((pct(mc_final,95)/INITIAL)**(1/YEARS)-1)*100:+.2f}%")

# 五年内最大回撤分布
print(f"\n五年内最大回撤分布 (Monte Carlo):")
print(f"  中位回撤: {pct(mc_maxdd,50)*100:.1f}%")
print(f"  第95分位: {pct(mc_maxdd,95)*100:.1f}%")

profit = sum(1 for v in mc_final if v > INITIAL) / N * 100
print(f"\n盈利概率: {profit:.1f}%")
