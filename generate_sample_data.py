# -*- coding: utf-8 -*-
"""
生成12只标的的模拟历史数据
"""

import os
import numpy as np
import pandas as pd

def generate_sample_kline(code, name, years=5):
    days = int(years * 252)
    dates = pd.date_range(end='2024-12-31', periods=days, freq='B')
    
    np.random.seed(int(code))
    base_price = np.random.uniform(5, 50)
    
    returns = np.random.normal(0.0003, 0.015, days)
    prices = base_price * np.cumprod(1 + returns)
    
    high = prices * (1 + np.random.uniform(0, 0.02, days))
    low = prices * (1 - np.random.uniform(0, 0.02, days))
    open_ = prices[:-1]
    open_ = np.insert(open_, 0, base_price)
    
    volumes = np.random.randint(1000000, 50000000, days)
    
    df = pd.DataFrame({
        'date': dates,
        'open': open_,
        'high': high,
        'low': low,
        'close': prices,
        'volume': volumes
    })
    
    df.set_index('date', inplace=True)
    return df

stocks = [
    ("600989", "宝丰能源"),
    ("600875", "东方电气"),
    ("600089", "特变电工"),
    ("600406", "国电南瑞"),
    ("600268", "国电南自"),
    ("300274", "阳光电源"),
    ("600995", "南网储能"),
    ("002371", "北方华创"),
    ("600276", "恒瑞医药"),
    ("688017", "绿的谐波"),
    ("000425", "徐工机械"),
]

cache_dir = 'data/cache'
os.makedirs(cache_dir, exist_ok=True)

print("生成模拟历史数据...")
for code, name in stocks:
    df = generate_sample_kline(code, name)
    filepath = os.path.join(cache_dir, f'kline_{code}_daily.parquet')
    df.to_parquet(filepath)
    print(f"  {code} {name}: {len(df)}条")

print("数据生成完成！")
