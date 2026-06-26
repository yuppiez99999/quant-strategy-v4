# -*- coding: utf-8 -*-
"""
12只标的量化策略 - 数据下载脚本
使用 iFinD MCP API 下载历史数据
"""

import os
import sys
import time
import yaml
import pandas as pd
from datetime import datetime, timedelta

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.join(os.path.dirname(base_dir), 'auto_trading_system', 'core'))


def load_config():
    with open(os.path.join(base_dir, 'config', 'portfolio.yaml'), 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def download_ifind_data(code: str, days: int = 500):
    try:
        from ifind_client import IFindClient
        client = IFindClient()
        raw = client.get_historical_klines(code, days=days)
        if not raw:
            return None

        rows = []
        for item in raw:
            date_str = str(item.get('日期', '')).strip()
            if not date_str:
                continue
            try:
                rows.append({
                    'date': pd.to_datetime(date_str),
                    'open': float(item.get('开盘价', 0) or 0),
                    'close': float(item.get('收盘价', 0) or 0),
                    'high': float(item.get('最高价', 0) or 0),
                    'low': float(item.get('最低价', 0) or 0),
                    'volume': float(item.get('成交量', 0) or 0)
                })
            except Exception:
                pass

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df = df.set_index('date').sort_index()
        for col in ['open', 'close', 'high', 'low', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df[df['close'] > 0]
        return df
    except Exception:
        return None


def download_sina_data(code: str, days: int = 500):
    try:
        import akshare as ak
        if code.startswith('5'):
            df = ak.fund_etf_hist_sina(symbol=code)
        else:
            if code.startswith('6'):
                symbol = f'sh{code}'
            elif code.startswith('0') or code.startswith('3'):
                symbol = f'sz{code}'
            else:
                symbol = f'sh{code}'

            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            df = ak.stock_zh_a_hist(symbol=code, period='daily', start_date=start_date, end_date=end_date, adjust='qfq')
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume'
            })
            df = df.set_index('date')
            df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return None


def main():
    portfolio = load_config()
    cache_dir = os.path.join(base_dir, 'data', 'cache')
    os.makedirs(cache_dir, exist_ok=True)

    print("=" * 60)
    print("12只标的量化策略 - 数据下载")
    print("=" * 60)

    success_count = 0
    for asset in portfolio['assets']:
        code = asset['code']
        name = asset['name']
        print(f"\n下载 {code} {name}...")

        df = download_ifind_data(code, days=800)
        if df is None or len(df) < 50:
            df = download_sina_data(code, days=800)

        if df is not None and len(df) >= 50:
            cache_file = os.path.join(cache_dir, f'kline_{code}_daily.parquet')
            df.to_parquet(cache_file)
            print(f"  ✓ 成功: {len(df)}条记录")
            success_count += 1
        else:
            print(f"  ✗ 失败")

    print("\n" + "=" * 60)
    print(f"下载完成: {success_count}/{len(portfolio['assets'])}")
    print("=" * 60)


if __name__ == '__main__':
    main()
