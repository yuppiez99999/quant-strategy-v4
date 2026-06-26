#!/usr/bin/env python
# -*- coding: utf-8 -*-
import shutil
import os

src_dir = r"E:\各种PY程序\auto_trading_system\data\cache"
dst_dir = r"E:\各种PY程序\12只标的量化策略\data\cache"

files = [
    "kline_510300_daily.parquet",
    "kline_518880_daily.parquet",
    "kline_512890_daily.parquet",
    "kline_601088_daily.parquet",
    "kline_511090_daily.parquet",
    "kline_511260_daily.parquet",
    "kline_159981_daily.parquet",
    "kline_159980_daily.parquet",
    "kline_511880_daily.parquet",
    "kline_513500_daily.parquet",
    "kline_600519_daily.parquet",
    "kline_000858_daily.parquet",
]

for f in files:
    src = os.path.join(src_dir, f)
    dst = os.path.join(dst_dir, f)
    if os.path.exists(src):
        shutil.copy(src, dst)
        print(f"复制 {f} 成功")
    else:
        print(f"文件 {f} 不存在")

print("\n复制完成")
