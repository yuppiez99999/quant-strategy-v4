#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充缺失的5只标的日K线数据
优先使用 Wind MCP API，额度不足时回退到 akshare 新浪数据源
保存格式: Parquet data/cache/kline_{code}_daily.parquet (日期索引 + OHLCV列)
"""

import subprocess
import json
import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============ 配置 ============
SKILL_DIR = os.path.expanduser("~/.agents/skills/wind-mcp-skill")
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# 5只缺失标的: 纯数字代码 → (Wind代码, 名称)
MISSING_STOCKS = [
    ("688981", "688981.SH", "中芯国际"),
    ("300750", "300750.SZ", "宁德时代"),
    ("300124", "300124.SZ", "汇川技术"),
    ("002475", "002475.SZ", "立讯精密"),
    ("603259", "603259.SH", "药明康德"),
]

DATE_START = "20210101"
DATE_END   = "20260606"

NODE_PATH = r"C:\Program Files\nodejs\node.exe"
if not os.path.exists(NODE_PATH):
    for p in os.environ.get("PATH", "").split(";"):
        test = os.path.join(p, "node.exe")
        if os.path.exists(test):
            NODE_PATH = test
            break

# ============ 方法1: Wind MCP ============

def call_wind_stock_kline(windcode: str) -> dict:
    """通过 Wind MCP CLI 获取单只股票日K线，对超时和临时不可用错误自动重试（最多2次，间隔3秒）"""
    params = json.dumps({
        "windcode": windcode,
        "begin_date": DATE_START,
        "end_date": DATE_END,
    })
    cmd = [
        NODE_PATH,
        "scripts/cli.mjs", "call", "stock_data", "get_stock_kline",
        params,
    ]
    env = os.environ.copy()
    env["http_proxy"] = ""
    env["https_proxy"] = ""

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                cmd, cwd=SKILL_DIR, capture_output=True, text=True,
                timeout=60, env=env
            )
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                print(f"      Wind MCP 超时，3秒后重试({attempt+1}/{max_retries})...")
                time.sleep(3)
                continue
            raise Exception("Wind MCP 超时")
        except FileNotFoundError:
            raise Exception(f"node 未找到: {NODE_PATH}")

        stdout = result.stdout.strip()
        if not stdout:
            raise Exception(f"MCP 无输出, stderr:{result.stderr[-200:]}")

        json_start = 0
        for i, ch in enumerate(stdout):
            if ch in "{[":
                json_start = i
                break
        if json_start > 0:
            stdout = stdout[json_start:]

        data = json.loads(stdout)

        if data.get("ok") is False or data.get("isError"):
            err = data.get("error", {})
            msg = str(err.get("agent_action", err.get("message", err)))[:200]
            # 检查临时不可用错误
            err_code = err.get('code', '') if isinstance(err, dict) else ''
            if err_code == 'TEMPORARILY_UNAVAILABLE' and attempt < max_retries:
                print(f"      Wind MCP 临时不可用，3秒后重试({attempt+1}/{max_retries})...")
                time.sleep(3)
                continue
            raise Exception(msg)

        content = data.get("content", [])
        if content:
            text = content[0].get("text", "{}")
            inner = json.loads(text)
            return inner

        raise Exception("content 为空")


def parse_wind_to_df(raw: dict) -> pd.DataFrame:
    """Wind 返回 → DataFrame"""
    data_block = raw.get("data", {})
    if data_block is None:
        raise Exception("data=null")
    columns = [c["name"] for c in data_block.get("columns", [])]
    rows = data_block.get("rows", [])
    if not rows:
        raise Exception("0条记录")

    df = pd.DataFrame(rows, columns=columns)
    col_map = {}
    for c in columns:
        cl = c.strip()
        if "日期" in cl:    col_map[c] = "date"
        elif "开盘" in cl:  col_map[c] = "open"
        elif "收盘" in cl:  col_map[c] = "close"
        elif "最高" in cl:  col_map[c] = "high"
        elif "最低" in cl:  col_map[c] = "low"
        elif "成交量" in cl: col_map[c] = "volume"
    df.rename(columns=col_map, inplace=True)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        if hasattr(df["date"].dt, "tz") and df["date"].dt.tz is not None:
            df["date"] = df["date"].dt.tz_localize(None)
        df["date"] = df["date"].dt.normalize()
        df = df.set_index("date").sort_index()
    for c in ["open","close","high","low","volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["close"] > 0]
    keep = [c for c in ["open","close","high","low","volume"] if c in df.columns]
    return df[keep]


# ============ 方法2: akshare 新浪数据源 ============

def download_akshare(code: str, days: int = 2000, retry: int = 3) -> pd.DataFrame:
    """通过 akshare 新浪接口下载日K线（前复权），带重试和间隔"""
    import akshare as ak

    # 清除代理防干扰
    for k in ["http_proxy","https_proxy","HTTP_PROXY","HTTPS_PROXY","all_proxy","ALL_PROXY"]:
        os.environ.pop(k, None)

    if code.startswith(("6", "5")):
        symbol = f"sh{code}"
    elif code.startswith(("0","3")):
        symbol = f"sz{code}"
    else:
        symbol = f"sh{code}"

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    last_err = ""
    for attempt in range(retry):
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                    start_date=start_date, end_date=end_date,
                                    adjust="qfq")
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    "日期": "date", "开盘": "open", "收盘": "close",
                    "最高": "high", "最低": "low", "成交量": "volume",
                })
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()
                for c in ["open","close","high","low","volume"]:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
                df = df[df["close"] > 0]
                if len(df) >= 200:
                    return df[["open","close","high","low","volume"]]
                else:
                    last_err = f"数据量不足: {len(df)}条"
            else:
                last_err = "akshare返回空"
        except Exception as e:
            last_err = str(e)[:100]
        if attempt < retry - 1:
            time.sleep(1)
    raise Exception(last_err)


# ============ 方法3: akshare 东方财富备用 ============

def download_akshare_eastmoney(code: str, days: int = 2000, retry: int = 3) -> pd.DataFrame:
    """通过 akshare 东方财富接口下载（备用），带重试"""
    import akshare as ak
    for k in ["http_proxy","https_proxy","HTTP_PROXY","HTTPS_PROXY","all_proxy","ALL_PROXY"]:
        os.environ.pop(k, None)

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    last_err = ""
    for attempt in range(retry):
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                    start_date=start_date, end_date=end_date,
                                    adjust="qfq")
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    "日期": "date", "开盘": "open", "收盘": "close",
                    "最高": "high", "最低": "low", "成交量": "volume",
                })
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()
                for c in ["open","close","high","low","volume"]:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
                df = df[df["close"] > 0]
                if len(df) >= 200:
                    return df[["open","close","high","low","volume"]]
                else:
                    last_err = f"东财数据量不足: {len(df)}条"
            else:
                last_err = "东财返回空"
        except Exception as e:
            last_err = str(e)[:100]
        if attempt < retry - 1:
            time.sleep(3)
    raise Exception(last_err)


# ============ 主流程 ============

def fetch_one(code: str, wind_code: str, name: str) -> pd.DataFrame:
    """三路回退获取单只股票K线: Wind MCP → akshare新浪 → akshare东财"""
    errors = []

    # 方法1: Wind MCP
    try:
        raw = call_wind_stock_kline(wind_code)
        df = parse_wind_to_df(raw)
        if len(df) >= 200:
            print(f"      来源: Wind MCP")
            return df
    except Exception as e:
        errors.append(f"Wind: {str(e)[:80]}")

    # 方法2: akshare 新浪
    try:
        df = download_akshare(code, days=2000)
        if len(df) >= 200:
            print(f"      来源: akshare (新浪)")
            return df
    except Exception as e:
        errors.append(f"akshare: {str(e)[:80]}")

    # 方法3: akshare 东方财富
    try:
        df = download_akshare_eastmoney(code, days=2000)
        if len(df) >= 200:
            print(f"      来源: akshare (东财)")
            return df
    except Exception as e:
        errors.append(f"东财: {str(e)[:80]}")

    raise Exception(" | ".join(errors))


def main():
    print("=" * 60)
    print("补充缺失K线数据 (Wind MCP → akshare 三路回退)")
    print(f"目标: 5只标的  区间: {DATE_START} ~ {DATE_END}")
    print("=" * 60)

    ok, fail = [], []

    def _fetch_one_stock(raw_code, wind_code, name):
        """并行下载单只标的K线"""
        print(f"\n▶ {raw_code} {name} ...", end=" ", flush=True)
        try:
            df = fetch_one(raw_code, wind_code, name)
            cache_file = os.path.join(CACHE_DIR, f"kline_{raw_code}_daily.parquet")
            try:
                df.to_parquet(cache_file)
            except Exception:
                csv_file = os.path.join(CACHE_DIR, f"kline_{raw_code}_daily.csv")
                df.to_csv(csv_file, encoding="utf-8-sig")
                print(f"      ⚠️ parquet不可用, 已存为CSV")
            print(f"      ✅ {len(df)}条  {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
            return (raw_code, name, len(df), None)
        except Exception as e:
            print(f"      ❌ {str(e)[:120]}")
            return (raw_code, name, None, str(e)[:120])

    with ThreadPoolExecutor(max_workers=min(5, len(MISSING_STOCKS))) as pool:
        futures = {pool.submit(_fetch_one_stock, rc, wc, n): rc for rc, wc, n in MISSING_STOCKS}
        for f in as_completed(futures):
            raw_code, name, cnt, err = f.result()
            if cnt is not None:
                ok.append((raw_code, name, cnt))
            else:
                fail.append((raw_code, name, err))

    print("\n" + "=" * 60)
    print(f"汇总: ✅ {len(ok)}/{len(MISSING_STOCKS)}  失败: {len(fail)}")
    for c, n, cnt in ok:
        print(f"  ✅ {c} {n}: {cnt}条")
    for c, n, err in fail:
        print(f"  ❌ {c} {n}: {err}")
    print("=" * 60)


if __name__ == "__main__":
    main()
