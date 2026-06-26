# -*- coding: utf-8 -*-
"""
全量 K 线数据下载/刷新脚本
数据源: 新浪 K 线 API (直连, 禁用代理)
功能:
  1. 扫描 portfolio.yaml 全部标的
  2. 缺失的 → 下载
  3. 已存在但数据过期(早于 today-7天) → 追加最新数据
  4. 空文件/损坏文件 → 重新下载
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 强制禁用代理
for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'):
    os.environ[k] = ''
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

import time
import json
import re
import yaml
import pandas as pd
import requests
from datetime import datetime, timedelta

# 全局禁用代理
_original_session_init = requests.Session.__init__
def _patched_init(self, *args, **kwargs):
    _original_session_init(self, *args, **kwargs)
    self.trust_env = False
    self.proxies = {'http': '', 'https': ''}
requests.Session.__init__ = _patched_init

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, 'data', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

DAYS = 1500  # 约 6 年历史
STALE_DAYS = 7  # 超过 7 天没更新视为过期


def download_sina_kline(code: str, market: str, days: int = DAYS) -> pd.DataFrame:
    """新浪 K 线 API"""
    url = f'https://quotes.sina.cn/cn/api/jsonp_v2.php/=/CN_MarketDataService.getKLineData'
    params = {
        'symbol': f'{market}{code}',
        'scale': 240,  # 日K
        'ma': 'no',
        'datalen': days,
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://finance.sina.com.cn/'
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20,
                            proxies={'http': '', 'https': ''})
        resp.raise_for_status()
        text = resp.text
        m = re.search(r'\((.*)\)', text, re.S)
        if not m:
            return None
        data = json.loads(m.group(1))
        if not data:
            return None
        df = pd.DataFrame(data)
        df = df.rename(columns={
            'day': 'date', 'open': 'open', 'high': 'high',
            'low': 'low', 'close': 'close', 'volume': 'volume'
        })
        for col in ['open', 'close', 'high', 'low', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        df = df[df['close'] > 0]
        # 归一化索引到纯日期(避免 00:00 vs 22:00 等时间差异导致去重失败)
        df.index = df.index.normalize()
        # 只保留核心列
        df = df[['open', 'close', 'high', 'low', 'volume']]
        df = df[~df.index.duplicated(keep='last')]
        return df
    except Exception as e:
        print(f'      错误: {e}')
        return None


def guess_market(code: str) -> str:
    """根据代码判断市场"""
    if code.startswith('6') or code.startswith('5') or code.startswith('9'):
        return 'sh'
    elif code.startswith('0') or code.startswith('3') or code.startswith('1') or code.startswith('2'):
        return 'sz'
    return 'sh'


def get_existing_kline(code: str):
    """读取已有的 K 线数据"""
    fp = os.path.join(CACHE_DIR, f'kline_{code}_daily.parquet')
    if not os.path.exists(fp):
        return None, None
    try:
        df = pd.read_parquet(fp)
        if df.empty:
            return None, fp
        return df, fp
    except Exception:
        return None, fp


def main():
    with open(os.path.join(BASE_DIR, 'config', 'portfolio.yaml'), 'r', encoding='utf-8') as f:
        portfolio = yaml.safe_load(f)

    today = datetime.now().date()
    stale_threshold = today - timedelta(days=STALE_DAYS)

    print('=' * 70)
    print(f'  全量 K 线数据刷新 ({today})')
    print(f'  过期阈值: {stale_threshold} (超过 {STALE_DAYS} 天视为过期)')
    print('=' * 70)

    results = []
    total = 0
    for asset in portfolio['assets']:
        code = asset['code']
        name = asset['name']
        if code == 'CASH':
            continue
        total += 1
        market = guess_market(code)
        fp = os.path.join(CACHE_DIR, f'kline_{code}_daily.parquet')

        existing_df, _ = get_existing_kline(code)
        status = 'NEW'
        if existing_df is not None:
            last_date = existing_df.index[-1].date()
            if last_date >= stale_threshold:
                status = 'FRESH'
            else:
                status = 'STALE'

        print(f'\n[{code}] {name} ({market}{code}) - {status}')
        if existing_df is not None:
            print(f'   现有: {len(existing_df)} 条, 最新 {existing_df.index[-1].date()}')

        if status == 'FRESH':
            print('   ✅ 数据新鲜,跳过')
            results.append((code, name, len(existing_df), existing_df.index[0].date(),
                           existing_df.index[-1].date(), 'SKIP', 0))
            continue

        start = time.time()
        df_new = download_sina_kline(code, market, DAYS)
        elapsed = time.time() - start

        if df_new is None or len(df_new) < 50:
            print(f'   ❌ 下载失败 ({elapsed:.1f}s)')
            results.append((code, name, 0, '-', '-', 'FAIL', elapsed))
            continue

        # 合并新旧数据(去重)
        if existing_df is not None:
            df_merged = pd.concat([existing_df, df_new])
            df_merged = df_merged[~df_merged.index.duplicated(keep='last')]
            df_merged = df_merged.sort_index()
            saved = df_merged
            action = 'MERGED'
            added = len(df_merged) - len(existing_df)
        else:
            saved = df_new
            action = 'NEW'
            added = len(df_new)

        saved.to_parquet(fp)
        start_d, end_d = saved.index[0].date(), saved.index[-1].date()
        last_close = float(saved['close'].iloc[-1])
        print(f'   ✅ {action}  共 {len(saved)} 条  新增 {added} 条  '
              f'{start_d} ~ {end_d}  ({elapsed:.1f}s)')
        print(f'   最新价: ¥{last_close:.2f}')
        results.append((code, name, len(saved), start_d, end_d, action, elapsed))

        time.sleep(0.2)

    # 汇总
    print('\n' + '=' * 70)
    print('  汇总')
    print('=' * 70)
    fresh = sum(1 for r in results if r[5] == 'SKIP')
    new = sum(1 for r in results if r[5] == 'NEW')
    merged = sum(1 for r in results if r[5] == 'MERGED')
    fail = sum(1 for r in results if r[5] == 'FAIL')
    print(f'  总标的: {total}')
    print(f'  新鲜跳过: {fresh}')
    print(f'  新下载: {new}')
    print(f'  追加更新: {merged}')
    print(f'  失败: {fail}')

    if fail > 0:
        print('\n  ❌ 失败列表:')
        for code, name, n, s, e, status, t in results:
            if status == 'FAIL':
                print(f'     {code} {name}')

    # 写日志
    log_path = os.path.join(CACHE_DIR, 'download_log.txt')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f'下载时间: {datetime.now()}\n')
        f.write(f'总标的: {total}  新鲜: {fresh}  新增: {new}  更新: {merged}  失败: {fail}\n\n')
        for code, name, n, s, e, status, t in results:
            f.write(f'{status:<8} {code:<10} {name:<10} {n:>5}条  {s} ~ {e}  ({t:.1f}s)\n')
    print(f'\n  日志: {log_path}')


if __name__ == '__main__':
    main()
