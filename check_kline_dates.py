# -*- coding: utf-8 -*-
"""检查每只标的 K 线数据时间跨度"""
import os
import pandas as pd

cache_dir = 'data/cache'
codes = ['510300', '510500', '512100', '588000', '159915',
         '688041', '300308', '300274', '600900', '600519',
         '601088', '600036', '601318', '518880', '600989',
         '600276', '002371', '600995', '600875', '600406',
         '000425', '600089', '688017']

for code in codes:
    fp = os.path.join(cache_dir, f'kline_{code}_daily.parquet')
    if not os.path.exists(fp):
        print(f'{code}: 缺失')
        continue
    df = pd.read_parquet(fp)
    end = df.index[-1]
    rows = len(df)
    last_close = float(df['close'].iloc[-1])
    print(f'{code}: {df.index[0].date()} ~ {end.date()}  ({rows}行, 最新¥{last_close:.2f})')
