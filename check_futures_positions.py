# -*- coding: utf-8 -*-
"""期货持仓情况检查"""
import json
import os
from datetime import datetime

trade_log_dir = r'e:\各种PY程序\11_量化策略\trade_logs'
futures_codes = ['CU', 'AL', 'RB', 'HC', 'SC', 'TA', 'PP', 'MA', 'C', 'A', 'LH', 'SR', 'LC', 'SI', 'SN']

print("=" * 60)
print("期货持仓情况报告")
print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 读取所有交易日志
trade_files = [f for f in os.listdir(trade_log_dir) if f.endswith('.json')]
signals = []

for tf in trade_files:
    try:
        with open(os.path.join(trade_log_dir, tf), 'r', encoding='utf-8') as f:
            data = json.load(f)
            signals.append(data)
    except:
        pass

# 按品种汇总
by_symbol = {}
for sig in signals:
    sym = sig.get('symbol', '')
    if sym not in by_symbol:
        by_symbol[sym] = []
    by_symbol[sym].append(sig)

print(f"\n[DATA] 交易信号统计:")
print(f"   总信号数: {len(signals)}")
print(f"   涉及品种: {len(by_symbol)}个")

print(f"\n{'-' * 60}")
print("[LIST] 各品种持仓详情:")
print(f"{'-' * 60}")

for symbol in futures_codes:
    if symbol in by_symbol:
        sigs = by_symbol[symbol]
        print(f"\n  {symbol} ({len(sigs)}个信号)")
        for s in sigs:
            print(f"    - {s.get('direction', '')} @ {s.get('entry_price', 0):.0f}")
            print(f"      时间: {s.get('entry_time', '')}")
            print(f"      状态: {s.get('status', '')}")
    else:
        print(f"\n  {symbol}: 无持仓")

print(f"\n{'-' * 60}")
print("[CASH] 当前期货账户状态:")
print(f"{'-' * 60}")

# 统计多空信号
long_signals = [s for s in signals if '多头' in s.get('direction', '')]
short_signals = [s for s in signals if '空头' in s.get('direction', '')]

print(f"   多头信号: {len(long_signals)}个")
print(f"   空头信号: {len(short_signals)}个")
print(f"   活跃持仓: {len([s for s in signals if s.get('status') == 'open'])}个")

print(f"\n{'=' * 60}")
print("[WARN] 注意: 当前为信号模拟阶段,尚未接入实盘交易")
print(f"{'=' * 60}")
