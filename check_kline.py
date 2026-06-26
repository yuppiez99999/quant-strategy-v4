# -*- coding: utf-8 -*-
"""检查 K 线数据子集"""
import os
import yaml

cache_dir = 'data/cache'
with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
    p = yaml.safe_load(f)

have = []
missing = []
for a in p['assets']:
    if a['code'] == 'CASH':
        continue
    fp = os.path.join(cache_dir, f'kline_{a["code"]}_daily.parquet')
    if os.path.exists(fp):
        have.append((a['code'], a['name']))
    else:
        missing.append((a['code'], a['name'], a.get('target_weight', 0)))

print(f'有数据: {len(have)} 只')
for c, n in have:
    print(f'  {c:<10} {n}')

print(f'\n缺失数据: {len(missing)} 只')
total_w_missing = 0
for c, n, w in missing:
    print(f'  {c:<10} {n:<10} 目标权重 {w*100:.0f}%')
    total_w_missing += w
print(f'缺失标的合计目标权重: {total_w_missing*100:.1f}%')
