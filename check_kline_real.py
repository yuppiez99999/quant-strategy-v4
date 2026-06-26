# -*- coding: utf-8 -*-
"""检查 K 线数据真实性"""
import os
import pandas as pd

cache_dir = 'data/cache'
codes_to_check = ['510300', '600519', '002371', '300274', '518880', '600276']

for code in codes_to_check:
    fp = os.path.join(cache_dir, f'kline_{code}_daily.parquet')
    if not os.path.exists(fp):
        print(f'{code}: 缺失')
        continue
    df = pd.read_parquet(fp)
    print(f'\n{code}: {len(df)} 条, {df.index[0].date()} ~ {df.index[-1].date()}')
    # 看几个关键时点
    for check_date in ['2024-01-15', '2024-06-30', '2024-12-31']:
        try:
            idx = df.index.get_indexer([pd.Timestamp(check_date)], method='ffill')[0]
            if idx >= 0:
                price = float(df['close'].iloc[idx])
                print(f'  {check_date}: ¥{price:.2f}')
        except Exception as e:
            print(f'  {check_date}: 错误 {e}')
    # 总体涨跌幅
    if len(df) >= 252:
        p_start = float(df['close'].iloc[-252])
        p_end = float(df['close'].iloc[-1])
        ret = (p_end / p_start - 1) * 100
        print(f'  近1年涨跌: {ret:+.2f}%')
