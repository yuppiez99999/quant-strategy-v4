# -*- coding: utf-8 -*-
"""检查当前 24 只标的 K 线数据完整度"""
import os
import yaml
import pandas as pd

CACHE_DIR = 'data/cache'

with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
    portfolio = yaml.safe_load(f)

print('=' * 70)
print('  24 只标的 K 线数据完整度检查')
print('=' * 70)

have = []
missing = []
for a in portfolio['assets']:
    code = a['code']
    name = a['name']
    if code == 'CASH':
        continue
    fp = os.path.join(CACHE_DIR, f'kline_{code}_daily.parquet')
    if not os.path.exists(fp):
        missing.append((code, name, '❌ 文件不存在'))
        continue
    df = pd.read_parquet(fp)
    if df.empty:
        missing.append((code, name, '❌ 空文件'))
        continue
    rows = len(df)
    start = df.index[0].date()
    end = df.index[-1].date()
    last_close = float(df['close'].iloc[-1])
    have.append((code, name, rows, start, end, last_close))

print(f'\n  ✅ 有数据: {len(have)}/{len(portfolio["assets"]) - 1}')
for code, name, n, s, e, p in have:
    print(f'     {code:<10} {name:<12} {n:>5}条  {s} ~ {e}  ¥{p:.2f}')

if missing:
    print(f'\n  ❌ 缺失: {len(missing)} 只')
    for code, name, reason in missing:
        print(f'     {code:<10} {name:<12} {reason}')

print('\n' + '=' * 70)
