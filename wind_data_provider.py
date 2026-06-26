# -*- coding: utf-8 -*-
"""
统一行情数据提供层 — Wind / iFinD / 免费数据源多级回退

数据源优先级:
  1. Wind MCP analytics_data (最稳, NL查询, ~3-11s)
  2. Wind MCP stock_data/fund_data (快, ~1.3s, 偶尔不可用)
  3. iFinD MCP (需配置IFIND_TOKEN, ~1-3s)
  4. 免费数据源回退层 (Wind/iFinD都不可用时使用):
     - akshare: 免费、最全面的中文金融数据接口
     - tushare: 经典A股/期货数据接口
     - baostock: 免费A股/指数数据
     - efinance: 轻量级东方财富数据接口
     - yahoo-finance2: 雅虎财经数据接口
     - pandas-datareader: 统一数据读取接口
  5. 新浪财经 API (免费备用, ~0.3s, 仅交易时间)

使用方式:
  from wind_data_provider import get_quotes_batch
  quotes = get_quotes_batch(['601088','600995','300274'], ['518880'])
  # => {'601088': {'price': 48.24, 'change': -1.55, 'source': 'wind_analytics'}, ...}
"""

import json
import os
import sys
import time
import logging
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd  # 模块级导入，避免热路径重复import开销

from utils.console_encoding import setup_utf8_console

setup_utf8_console()

# ---- 日志 ----
_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(_log_dir, exist_ok=True)

_log = logging.getLogger('wind_data')
_log.setLevel(logging.DEBUG)
_fh = logging.FileHandler(
    os.path.join(_log_dir, 'wind_data_{:%Y%m%d}.log'.format(datetime.now())),
    encoding='utf-8'
)
_fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
_log.addHandler(_fh)
_sh = logging.StreamHandler()
_sh.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
_log.addHandler(_sh)

# ---- Wind CLI 配置 ----
WIND_CLI = os.environ.get(
    "WIND_CLI_PATH",
    os.path.expandvars(r"%USERPROFILE%\.agents\skills\wind-mcp-skill\scripts\cli.mjs")
)
WIND_API_KEY = os.environ.get('WIND_API_KEY', '')
WIND_TIMEOUT = int(os.environ.get('WIND_TIMEOUT', '35'))  # 单次调用超时(秒)
MAX_RETRIES = int(os.environ.get('WIND_RETRIES', '2'))

# ---- 缓存目录配置 ----
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# ---- 全局统计 ----
_stats_lock = threading.Lock()
_stats = {
    'total_calls': 0,
    'wind_analytics_ok': 0,
    'wind_direct_ok': 0,
    'ifind_ok': 0,
    'sina_ok': 0,
    'akshare_ok': 0,
    'tushare_ok': 0,
    'baostock_ok': 0,
    'efinance_ok': 0,
    'yahoo_ok': 0,
    'pdr_ok': 0,
    'all_failed': 0,
    'total_elapsed': 0.0,
}


def _incr_stat(key: str, delta: float = 1.0, count_total: bool = True):
    """线程安全地增加统计计数"""
    with _stats_lock:
        _stats[key] += delta
        if count_total and key not in ('total_elapsed',):
            _stats['total_calls'] += 1 if delta > 0 else 0


def _build_env() -> Dict[str, str]:
    """构建干净的环境变量(清除代理)"""
    env = os.environ.copy()
    env['WIND_API_KEY'] = WIND_API_KEY
    for k in list(env.keys()):
        kl = k.lower()
        if kl in ('http_proxy', 'https_proxy', 'http_proxy', 'https_proxy'):
            del env[k]
    env['no_proxy'] = '*'
    return env


# ============================================================
# 第一层: Wind MCP analytics_data (NL查询, 最稳定)
# ============================================================

def _wind_analytics_query(windcode: str) -> Optional[Dict]:
    """通过 analytics_data 接口查询单个标的"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            cmd = [
                'node', WIND_CLI, 'call', 'analytics_data',
                'get_financial_data',
                json.dumps({"question": f"查询A股{windcode}最新成交价和涨跌幅"})
            ]
            t0 = time.time()
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=WIND_TIMEOUT,
                env=_build_env(), encoding='utf-8', errors='replace'
            )
            elapsed = time.time() - t0

            if r.returncode != 0 or not r.stdout:
                _log.warning("[wind_analytics] %s attempt=%d rc=%d empty",
                            windcode, attempt, r.returncode)
                if attempt < MAX_RETRIES:
                    time.sleep(1.0 * attempt)
                    continue
                return None

            resp = json.loads(r.stdout)
            result = _parse_analytics_resp(resp, windcode)
            if result:
                _incr_stat('wind_analytics_ok')
                _log.info("[wind_analytics] %s price=%.2f chg=%.2f%% (%.1fs)",
                         windcode, result['price'], result['change'], elapsed)
                return {**result, 'source': 'wind_analytics'}

            _log.warning("[wind_analytics] %s attempt=%d parse failed", windcode, attempt)
        except subprocess.TimeoutExpired:
            _log.error("[wind_analytics] %s attempt=%d timeout >%ds", windcode, attempt, WIND_TIMEOUT)
        except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
            _log.warning("[wind_analytics] %s attempt=%d parse_err: %s", windcode, attempt, e)
        except Exception as e:
            _log.error("[wind_analytics] %s attempt=%d err: %s", windcode, attempt, e)

        if attempt < MAX_RETRIES:
            time.sleep(1.0 * attempt)
    return None


def _parse_analytics_resp(resp: dict, expected_code: str) -> Optional[Dict]:
    """
    解析 analytics_data 响应。
    实际返回结构 (从测试验证):
      content[0].text => JSON字符串 =>
        data.data[0].columns: [{name:"最新成交价",type:"number"}, ...]
        data.data[0].rows: [[price, change_pct, ...]]
    列顺序不固定，需按 name 匹配。
    """
    try:
        content_list = resp.get('content', [])
        if not content_list:
            return None
        raw_text = content_list[0].get('text', '')
        if not raw_text:
            return None

        inner = json.loads(raw_text)
        dataset_list = inner.get('data', {}).get('data', [])
        if not dataset_list:
            return None

        ds = dataset_list[0]
        columns = ds.get('columns', [])
        rows = ds.get('rows', [])
        if not rows or not rows[0]:
            return None

        # 构建 col_name -> index 映射
        col_map = {}
        for i, c in enumerate(columns):
            cname = c.get('name', '')
            col_map[cname] = i
            # 备选关键词匹配
            if '成交价' in cname and '最新' in cname:
                col_map['_price'] = i
            if '涨跌幅' in cname:
                col_map['_change'] = i

        row = rows[0]
        price = _get_col_val(row, col_map, ['最新成交价', '_price'])
        change = _get_col_val(row, col_map, ['最新涨跌幅', '_change'])

        if price is not None and price > 0:
            return {
                'price': float(price),
                'change': float(change) if change is not None else 0.0,
            }
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        pass
    return None


def _get_col_val(row: list, col_map: dict, keys: List[str]) -> Optional[float]:
    """按多个候选键名取值"""
    for k in keys:
        idx = col_map.get(k)
        if idx is not None and idx < len(row) and row[idx] is not None:
            try:
                v = float(row[idx])
                if v != 0 or k == '_price':
                    return v
            except (ValueError, TypeError):
                continue
    return None


# ============================================================
# 第二层: Wind MCP stock_data / fund_data (快但不稳定)
# ============================================================

def _wind_direct_query(code: str, is_fund: bool = False) -> Optional[Dict]:
    """通过 stock_data 或 fund_data 直接查询"""
    windcode = f'{code}.SH' if code.startswith(('6', '5')) else f'{code}.SZ'
    server = 'fund_data' if is_fund else 'stock_data'
    tool = 'get_fund_price_indicators' if is_fund else 'get_stock_price_indicators'

    params = {"windcode": windcode, "indexes": "最新成交价,涨跌幅"}

    try:
        cmd = ['node', WIND_CLI, 'call', server, tool, json.dumps(params)]
        t0 = time.time()
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
            env=_build_env(), encoding='utf-8', errors='replace'
        )
        elapsed = time.time() - t0

        if r.returncode != 0 or not r.stdout:
            # 检查是否是"服务暂时不可用"
            if 'temporarily_unavailable' in (r.stdout or '') or 'UNKNOWN' in str(r.returncode):
                _log.debug("[wind_direct] %s service unavailable (%.1fs)", windcode, elapsed)
            else:
                _log.debug("[wind_direct] %s rc=%d (%.1fs)", windcode, r.returncode, elapsed)
            return None

        resp = json.loads(r.stdout)
        content_list = resp.get('content', [])
        if not content_list:
            return None

        inner_text = content_list[0].get('text', '')
        inner = json.loads(inner_text)
        data_section = inner.get('data', {})
        rows = data_section.get('rows', [])

        if rows and rows[0]:
            # 处理非交易时段返回 INVALID 的情况
            price_val = rows[0][0]
            if isinstance(price_val, str) and price_val.upper() in ('INVALID', 'NONE', 'N/A', '—'):
                _log.debug("[wind_direct] %s non-trading hours (INVALID)", windcode)
                return None
            try:
                price = float(price_val)
            except (ValueError, TypeError):
                _log.debug("[wind_direct] %s err: could not convert price to float", code)
                return None
            
            change_val = rows[0][1] if len(rows[0]) > 1 else 0.0
            if isinstance(change_val, str) and change_val.upper() in ('INVALID', 'NONE', 'N/A', '—'):
                change = 0.0
            else:
                try:
                    change = float(change_val)
                except (ValueError, TypeError):
                    change = 0.0
            
            if price > 0:
                _incr_stat('wind_direct_ok')
                _log.info("[wind_direct] %s price=%.2f chg=%.2f%% (%.1fs)",
                         windcode, price, change, elapsed)
                return {'price': price, 'change': change, 'source': 'wind_direct'}
    except Exception as e:
        _log.debug("[wind_direct] %s err: %s", code, e)
    return None


# ============================================================
# 第三层: iFinD MCP (需配置 IFIND_TOKEN)
# ============================================================

_IFIND_CLIENT = None

def _get_ifind_client():
    """懒加载 iFinD 客户端"""
    global _IFIND_CLIENT
    if _IFIND_CLIENT is not None:
        return _IFIND_CLIENT
    token = os.environ.get('IFIND_TOKEN', '')
    if not token:
        return None
    try:
        from ifind_client import IFindClient
        _IFIND_CLIENT = IFindClient(auth_token=token, max_concurrency=2)
        _log.info("[ifind] client initialized")
        return _IFIND_CLIENT
    except ImportError:
        _log.warning("[ifind] ifind_client.py not found")
    except Exception as e:
        _log.error("[ifind] init failed: %s", e)
    _IFIND_CLIENT = False  # 标记为已尝试但失败
    return None


def _ifind_query(code: str, is_fund: bool = False) -> Optional[Dict]:
    """通过 iFinD 查询"""
    client = _get_ifind_client()
    if not client:
        return None
    try:
        if is_fund:
            quotes = client.get_etf_quotes([code])
            if code in quotes:
                q = quotes[code]
                _incr_stat('ifind_ok')
                _log.info("[ifind] %s price=%.2f chg=%.2f%%", code, q['price'], q['change_pct'])
                return {'price': q['price'], 'change': q['change_pct'], 'source': 'ifind'}
        else:
            # 用stock_daily获取最新收盘价作为近似
            result = client.call("stock", "stock_daily", {
                "query": f"{code}最近一天的开盘价、收盘价、最高价、最低价"
            })
            # 解析...简化版直接取最后一行收盘价
            from ifind_client import _parse_ifind_response, _col
            parsed = _parse_ifind_response(result)
            tables = parsed.get("tables", [])
            if tables:
                last_row = tables[-1]
                close_str = _col(last_row, "收盘价", "收盘") or "0"
                if close_str and float(close_str) > 0:
                    _incr_stat('ifind_ok')
                    _log.info("[ifind] %s close=%s", code, close_str)
                    return {'price': float(close_str), 'change': 0.0, 'source': 'ifind'}
    except Exception as e:
        _log.debug("[ifind] %s err: %s", code, e)
    return None


# ============================================================
# 第四层: 免费数据源回退层 (Wind/iFinD都不可用时使用)
# ============================================================

def _akshare_query(code: str, is_fund: bool = False) -> Optional[Dict]:
    """通过 akshare 查询 (免费、最全面的中文金融数据接口)"""
    try:
        import akshare as ak
        
        if is_fund:
            # ETF数据
            etf_data = ak.fund_etf_hist_sina(symbol=f"sh{code}" if code.startswith('5') else f"sz{code}")
            if not etf_data.empty:
                latest = etf_data.iloc[-1]
                price = float(latest['close'])
                if price > 0:
                    _incr_stat('sina_ok')
                    _incr_stat('akshare_ok', count_total=False)
                    _log.info("[akshare] %s price=%.2f (ETF)", code, price)
                    return {'price': price, 'change': 0.0, 'source': 'akshare'}
        else:
            # 股票数据
            stock_data = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="")
            if not stock_data.empty:
                latest = stock_data.iloc[-1]
                price = float(latest['收盘'])
                if price > 0:
                    change = float(latest['涨跌幅']) if '涨跌幅' in latest else 0.0
                    _incr_stat('sina_ok')
                    _incr_stat('akshare_ok', count_total=False)
                    _log.info("[akshare] %s price=%.2f chg=%.2f%%", code, price, change)
                    return {'price': price, 'change': change, 'source': 'akshare'}
    except ImportError:
        _log.debug("[akshare] akshare not installed")
    except Exception as e:
        _log.debug("[akshare] %s err: %s", code, e)
    return None


def _tushare_query(code: str, is_fund: bool = False) -> Optional[Dict]:
    """通过 tushare 查询 (经典A股/期货数据接口)"""
    try:
        import tushare as ts
        
        ts.set_token(os.environ.get('TUSHARE_TOKEN', ''))
        pro = ts.pro_api()
        
        if is_fund:
            # ETF数据
            df = pro.fund_daily(ts_code=f"{code}.SH" if code.startswith('5') else f"{code}.SZ", 
                               start_date=datetime.now().strftime('%Y%m%d'))
        else:
            # 股票数据
            df = pro.daily(ts_code=f"{code}.SH" if code.startswith('6') else f"{code}.SZ", 
                          start_date=datetime.now().strftime('%Y%m%d'))
        
        if not df.empty:
            latest = df.iloc[0]
            price = float(latest['close'])
            if price > 0:
                change = float(latest['pct_chg']) if 'pct_chg' in latest else 0.0
                _incr_stat('sina_ok')
                _incr_stat('tushare_ok', count_total=False)
                _log.info("[tushare] %s price=%.2f chg=%.2f%%", code, price, change)
                return {'price': price, 'change': change, 'source': 'tushare'}
    except ImportError:
        _log.debug("[tushare] tushare not installed")
    except Exception as e:
        _log.debug("[tushare] %s err: %s", code, e)
    return None


def _baostock_query(code: str, is_fund: bool = False) -> Optional[Dict]:
    """通过 baostock 查询 (免费A股/指数数据)"""
    try:
        import baostock as bs
        
        lg = bs.login()
        if lg.error_code != '0':
            _log.debug("[baostock] login failed: %s", lg.error_msg)
            return None
        
        windcode = f"{code}.SH" if code.startswith(('6', '5')) else f"{code}.SZ"
        
        rs = bs.query_history_k_data_plus(
            windcode,
            "date,close,changepercent",
            start_date=datetime.now().strftime('%Y-%m-%d'),
            frequency="d",
            adjustflag="3"
        )
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        if data_list:
            latest = data_list[-1]
            price = float(latest[1])
            if price > 0:
                change = float(latest[2]) if len(latest) > 2 else 0.0
                _incr_stat('sina_ok')
                _incr_stat('baostock_ok', count_total=False)
                _log.info("[baostock] %s price=%.2f chg=%.2f%%", code, price, change)
                bs.logout()
                return {'price': price, 'change': change, 'source': 'baostock'}
        bs.logout()
    except ImportError:
        _log.debug("[baostock] baostock not installed")
    except Exception as e:
        _log.debug("[baostock] %s err: %s", code, e)
        try:
            bs.logout()
        except Exception:
            pass
    return None


def _efinance_query(code: str, is_fund: bool = False) -> Optional[Dict]:
    """通过 efinance 查询 (轻量级东方财富数据接口)"""
    try:
        import efinance as ef
        
        if is_fund:
            # ETF数据
            data = ef.fund.get_quote_history(f"SH{code}" if code.startswith('5') else f"SZ{code}")
        else:
            # 股票数据
            data = ef.stock.get_quote_history(f"SH{code}" if code.startswith('6') else f"SZ{code}")
        
        if not data.empty:
            latest = data.iloc[-1]
            price = float(latest['收盘价'])
            if price > 0:
                change = float(latest['涨跌幅']) if '涨跌幅' in latest else 0.0
                _incr_stat('sina_ok')
                _incr_stat('efinance_ok', count_total=False)
                _log.info("[efinance] %s price=%.2f chg=%.2f%%", code, price, change)
                return {'price': price, 'change': change, 'source': 'efinance'}
    except ImportError:
        _log.debug("[efinance] efinance not installed")
    except Exception as e:
        _log.debug("[efinance] %s err: %s", code, e)
    return None


def _yahoo_finance_query(code: str, is_fund: bool = False) -> Optional[Dict]:
    """通过 yahoo-finance2 查询 (雅虎财经数据接口)"""
    try:
        from yahoo_finance import YahooFinance
        
        # 构建雅虎代码
        if code.startswith('6'):
            yahoo_code = f"{code}.SS"  # 上交所
        elif code.startswith('0') or code.startswith('3'):
            yahoo_code = f"{code}.SZ"  # 深交所
        else:
            return None
        
        yf = YahooFinance(yahoo_code)
        quote = yf.get_current_price()
        if quote and quote > 0:
            _incr_stat('sina_ok')
            _incr_stat('yahoo_ok', count_total=False)
            _log.info("[yahoo] %s price=%.2f", code, quote)
            return {'price': quote, 'change': 0.0, 'source': 'yahoo_finance'}
    except ImportError:
        _log.debug("[yahoo] yahoo-finance not installed")
    except Exception as e:
        _log.debug("[yahoo] %s err: %s", code, e)
    return None


def _pandas_datareader_query(code: str, is_fund: bool = False) -> Optional[Dict]:
    """通过 pandas-datareader 查询 (统一数据读取接口)"""
    try:
        import pandas_datareader as pdr
        
        # 构建雅虎代码
        if code.startswith('6'):
            yahoo_code = f"{code}.SS"
        elif code.startswith('0') or code.startswith('3'):
            yahoo_code = f"{code}.SZ"
        else:
            return None
        
        data = pdr.get_data_yahoo(yahoo_code, start=datetime.now().strftime('%Y-%m-%d'))
        if not data.empty:
            price = float(data['Close'].iloc[-1])
            if price > 0:
                _incr_stat('sina_ok')
                _incr_stat('pdr_ok', count_total=False)
                _log.info("[pdr] %s price=%.2f", code, price)
                return {'price': price, 'change': 0.0, 'source': 'pandas_datareader'}
    except ImportError:
        _log.debug("[pdr] pandas_datareader not installed")
    except Exception as e:
        _log.debug("[pdr] %s err: %s", code, e)
    return None


def _free_data_query(code: str, is_fund: bool = False) -> Optional[Dict]:
    """免费数据源回退查询 - 依次尝试所有免费数据源"""
    # 1. 新浪财经 API (免费、实时、响应快，优先尝试)
    result = _sina_query(code, is_fund)
    if result:
        return result
    
    # 2. efinance (轻量级东方财富)
    result = _efinance_query(code, is_fund)
    if result:
        return result
    
    # 3. akshare (最全面)
    result = _akshare_query(code, is_fund)
    if result:
        return result
    
    # 4. baostock (免费A股数据)
    result = _baostock_query(code, is_fund)
    if result:
        return result
    
    # 5. tushare (需要token)
    result = _tushare_query(code, is_fund)
    if result:
        return result
    
    # 6. yahoo-finance2 (国际品种)
    result = _yahoo_finance_query(code, is_fund)
    if result:
        return result
    
    # 7. pandas-datareader
    result = _pandas_datareader_query(code, is_fund)
    if result:
        return result
    
    return None


# ============================================================
# 第五层: 新浪财经 API (免费备用)
# ============================================================

def _sina_query(code: str, is_fund: bool = False) -> Optional[Dict]:
    """通过新浪财经 API 查询（仅交易时间有效）"""
    try:
        from sina_api_helper import get_sina_kline_latest
        if is_fund:
            # 新浪ETF接口: 代码以5或15开头的都是ETF
            is_etf = code.startswith('5') or code.startswith('15')
            prefix = 'sh' if is_etf else 'sz'
            result = get_sina_kline_latest(f"{prefix}{code}")
            if result and result.get('price', 0) > 0:
                price = result['price']
                change = result.get('change', 0)
                # 增加合理性验证: ETF单日波动超过5%视为异常数据
                if change and abs(change) > 5:
                    _log.warning("[sina] %s change=%.2f%% 超出合理范围, 视为异常数据丢弃", code, change)
                    return None
                _incr_stat('sina_ok')
                _log.info("[sina] %s price=%.2f chg=%.2f%%", code, price, change)
                return {'price': price, 'change': change, 'source': 'sina'}
        else:
            prefix = 'sh' if code.startswith('6') else 'sz'
            result = get_sina_kline_latest(f"{prefix}{code}")
            if result and result.get('price', 0) > 0:
                price = result['price']
                change = result.get('change', 0)
                # 增加合理性验证: 股票单日波动限制(主板10%, 科创板/创业板20%)
                max_change = 0.20 if code.startswith(('688', '300')) else 0.10
                if change and abs(change) > max_change:
                    _log.warning("[sina] %s change=%.2f%% 超出%s限制, 视为异常数据丢弃", code, change, "20%" if code.startswith(('688', '300')) else "10%")
                    return None
                _incr_stat('sina_ok')
                _log.info("[sina] %s price=%.2f chg=%.2f%%", code, price, change)
                return {'price': price, 'change': change, 'source': 'sina'}
    except ImportError:
        _log.debug("[sina] sina_api_helper.py not available")
    except Exception as e:
        _log.debug("[sina] %s err: %s", code, e)
    return None


# ---- 兜底价格配置（非交易时段使用）----
# 价格来源: positions.json 最新成交价
FALLBACK_PRICES = {
    # === 当前持仓标的 ===
    '601088': 40.28,   # 中国神华
    '600989': 22.11,   # 宝丰能源
    '600875': 30.41,   # 东方电气
    '300274': 151.60,  # 阳光电源
    '002371': 749.64,  # 北方华创
    '688017': 383.40,  # 绿的谐波
    '600900': 26.75,   # 长江电力
    '600519': 1222.63, # 贵州茅台
    '600036': 37.13,   # 招商银行
    '601318': 49.73,   # 中国平安
    '518880': 8.47,    # 黄金ETF
    '600995': 12.41,   # 南网储能
    '600406': 23.13,   # 国电南瑞
    '000425': 8.47,    # 徐工机械
    '600089': 23.46,   # 特变电工
    '600276': 50.68,   # 恒瑞医药
    '688041': 314.00,  # 中际旭创
    '300308': 1319.28, # 中际旭创
    # === 核心宽基ETF ===
    '510300': 4.94,    # 沪深300ETF
    '510500': 8.84,    # 中证500ETF
    '512100': 3.50,    # 中证1000ETF
    '588000': 2.04,    # 科创50ETF
    '159915': 4.21,    # 创业板ETF
}


def _get_fallback_price(code: str) -> Optional[Dict]:
    """获取兜底价格（非交易时段使用）"""
    price = FALLBACK_PRICES.get(code)
    if price:
        _log.info("[fallback] %s price=%.2f (predefined)", code, price)
        return {'price': price, 'change': 0.0, 'source': 'fallback'}
    return None


def _get_local_cache_price(code: str) -> Optional[Dict]:
    """从本地Parquet缓存获取最新收盘价（兜底方案）"""
    try:
        cache_file = os.path.join(CACHE_DIR, f'kline_{code}_daily.parquet')
        if os.path.exists(cache_file):
            df = pd.read_parquet(cache_file, columns=['close', 'trade_date'],
                                 engine='fastparquet' if 'fastparquet' in sys.modules else 'pyarrow')
            if not df.empty:
                # 获取最新日期的数据
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                latest_row = df[df['trade_date'] == df['trade_date'].max()]
                if not latest_row.empty:
                    price = latest_row['close'].iloc[0]
                    if price > 0:
                        _log.info("[local_cache] %s price=%.2f (from cache)", code, price)
                        return {'price': float(price), 'change': 0.0, 'source': 'local_cache'}
    except Exception as e:
        _log.debug("[local_cache] %s err: %s", code, e)
    return None


# ============================================================
# 统一查询入口 (单只)
# ============================================================

def _validate_price(code: str, price: float) -> bool:
    """验证价格是否合理（防止返回错误数据）"""
    # v5.3 优化版 — 覆盖全部37只标的的价格范围（权益组合22只 + 低风险理财15只）
    price_ranges = {
        # ===== 权益组合 =====
        
        # 核心宽基 ETF（5只）
        '510300': (3, 8),       # 沪深300ETF
        '510500': (4, 12),      # 中证500ETF
        '512100': (1, 8),       # 中证1000ETF
        '588000': (0.5, 3),     # 科创50ETF
        '159915': (1, 5),       # 创业板ETF
        
        # 科技成长个股（6只）
        '688041': (100, 300),   # 海光信息
        '300308': (500, 1500),  # 中际旭创
        '300274': (80, 250),    # 阳光电源
        '002371': (300, 800),   # 北方华创
        '688017': (200, 600),   # 绿的谐波
        '600276': (30, 80),     # 恒瑞医药
        
        # 高端制造/基建（5只）
        '600089': (15, 40),     # 特变电工
        '600875': (15, 50),     # 东方电气
        '000425': (5, 15),      # 徐工机械
        '600406': (15, 40),     # 国电南瑞
        '600989': (10, 30),     # 宝丰能源
        
        # 防御/红利（4只）
        '515180': (0.8, 3),     # 易方达中证红利ETF
        '600036': (20, 50),     # 招商银行
        '600900': (20, 40),     # 长江电力
        '601088': (30, 65),     # 中国神华
        
        # 商品/避险（1只）
        '518880': (5, 15),      # 黄金ETF
        
        # ===== 低风险理财 =====
        
        # 短债基金（2只）
        '000105': (0.9, 1.2),   # 易方达短债A
        '000084': (0.9, 1.2),   # 博时安盈短债A
        
        # 信用债基金（2只）
        '000236': (0.8, 1.3),   # 易方达信用债A
        '000267': (0.8, 1.3),   # 广发信用债A
        
        # 可转债基金（3只）
        '340001': (0.8, 2.0),   # 兴全可转债
        '001816': (0.8, 2.0),   # 中欧可转债A
        '040022': (0.8, 2.0),   # 华安可转债A
        
        # 红利/价值ETF（3只）
        '515080': (0.8, 3),     # 中证红利ETF
        '512890': (0.8, 3),     # 红利低波ETF
        '510030': (0.8, 3),     # 沪深300价值ETF
        
        # 增强型指数基金（2只）
        '000311': (0.5, 3.0),   # 易方达沪深300增强
        '163407': (0.5, 3.0),   # 兴全沪深300增强
    }
    
    expected_range = price_ranges.get(code)
    if expected_range:
        min_price, max_price = expected_range
        if price < min_price or price > max_price:
            _log.warning(f"[validate] {code} price={price} out of range [{min_price}, {max_price}]")
            return False
    
    # 国债逆回购代码（204xxx沪/1318xx深）- 特殊处理（利率而非价格）
    if code.startswith('204') or code.startswith('1318'):
        return True
    
    # 科创板688开头可能价格较高
    if code.startswith('688'):
        return 10 <= price <= 3000
    
    # 未在列表中的标的不做价格校验（新增标的自动通过）
    return True

def get_quote(code: str, is_fund: bool = False) -> Dict:
    """
    查询单只标的实时行情。
    按优先级依次尝试: Wind direct → Wind analytics → iFinD → 免费数据源 → 新浪 → 本地缓存 → 兜底价格
    返回: {'price': float, 'change': float, 'source': str}
           若全部失败: {'price': 0, 'change': 0, 'source': 'failed'}
    """
    _incr_stat('total_calls', count_total=False)
    t_start = time.time()

    # 0. Wind MCP 统一获取器 (最高优先 — 已验证可用)
    try:
        from wind_mcp_fetcher import wind_get_quote
        result = wind_get_quote(code, is_fund)
        if result and _validate_price(code, result['price']):
            _incr_stat('wind_direct_ok', count_total=False)
            result['elapsed'] = round(time.time() - t_start, 1)
            return result
    except ImportError:
        pass  # wind_mcp_fetcher 不可用时跳过
    except Exception as e:
        _log.debug("[wind_mcp_fetcher] %s err: %s", code, e)

    # 1. Wind direct (stock_data/fund_data, 更准确)
    result = _wind_direct_query(code, is_fund)
    if result and _validate_price(code, result['price']):
        result['elapsed'] = round(time.time() - t_start, 1)
        return result

    # 2. Wind analytics_data (NL查询, 作为备选)
    windcode = f'{code}.SH' if code.startswith(('6', '5')) else f'{code}.SZ'
    result = _wind_analytics_query(windcode)
    if result and _validate_price(code, result['price']):
        result['elapsed'] = round(time.time() - t_start, 1)
        return result

    # 3. iFinD
    result = _ifind_query(code, is_fund)
    if result:
        result['elapsed'] = round(time.time() - t_start, 1)
        return result

    # 4. 免费数据源回退层 (Wind/iFinD都不可用时使用)
    result = _free_data_query(code, is_fund)
    if result:
        result['elapsed'] = round(time.time() - t_start, 1)
        return result

    # 5. 新浪
    result = _sina_query(code, is_fund)
    if result:
        result['elapsed'] = round(time.time() - t_start, 1)
        return result

    # 6. 本地缓存
    result = _get_local_cache_price(code)
    if result:
        result['elapsed'] = round(time.time() - t_start, 1)
        return result

    # 7. 兜底价格（非交易时段使用）
    result = _get_fallback_price(code)
    if result:
        result['elapsed'] = round(time.time() - t_start, 1)
        return result

    # 全部失败
    elapsed = time.time() - t_start
    _incr_stat('all_failed')
    _incr_stat('total_elapsed', elapsed)
    _log.error("[FAIL] %s all sources exhausted (%.1fs)", code, elapsed)
    return {'price': 0, 'change': 0, 'source': 'failed', 'elapsed': round(elapsed, 1)}


# ============================================================
# 批量查询入口 (并发)
# ============================================================

def get_quotes_batch(stock_codes: List[str], fund_codes: Optional[List[str]] = None,
                     max_workers: int = 4) -> Dict[str, Dict]:
    """
    并发批量查询行情。
    
    Args:
        stock_codes: A股代码列表如 ['601088','600995']
        fund_codes: ETF/基金代码列表如 ['518880']
        max_workers: 最大并发数
    
    Returns:
        {code: {'price': float, 'change': float, 'source': str, 'elapsed': float}, ...}
    """
    fund_codes = fund_codes or []
    all_codes = [(c, False) for c in stock_codes] + [(c, True) for c in fund_codes]

    results = {}
    t_start = time.time()

    _log.info("[batch] start: %d stocks + %d funds, workers=%d",
             len(stock_codes), len(fund_codes), max_workers)

    # 0. Wind MCP 批量获取 (最高优先)
    try:
        from wind_mcp_fetcher import wind_get_batch_quotes
        # 分别批量获取股票和基金
        if stock_codes:
            stock_results = wind_get_batch_quotes(stock_codes, is_fund=False)
            for code, r in stock_results.items():
                if _validate_price(code, r.get('price', 0)):
                    _incr_stat('total_calls', count_total=False)
                    _incr_stat('wind_direct_ok', count_total=False)
                    results[code] = {**r, 'elapsed': round(time.time() - t_start, 1)}
        if fund_codes:
            fund_results = wind_get_batch_quotes(fund_codes, is_fund=True)
            for code, r in fund_results.items():
                if _validate_price(code, r.get('price', 0)):
                    _incr_stat('total_calls', count_total=False)
                    _incr_stat('wind_direct_ok', count_total=False)
                    results[code] = {**r, 'elapsed': round(time.time() - t_start, 1)}
        if results:
            _log.info("[batch] wind_mcp_fetcher got %d/%d", len(results), len(all_codes))
    except ImportError:
        pass
    except Exception as e:
        _log.debug("[batch] wind_mcp_fetcher err: %s", e)

    # 仅对未获取到的代码走回退链
    remaining = [(c, is_f) for c, is_f in all_codes if c not in results]
    if not remaining:
        total_time = time.time() - t_start
        ok_count = len(results)
        _log.info("[batch] done (all from wind_mcp): %d/%d ok in %.1fs", ok_count, len(results), total_time)
        try:
            print(f"\n  done: {ok_count}/{len(results)} ok ({total_time:.1f}s) [wind_mcp({ok_count})]")
        except Exception:
            pass
        return results

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_code = {
            executor.submit(get_quote, code, is_f): code
            for code, is_f in remaining
        }
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            try:
                results[code] = future.result()
            except Exception as e:
                _log.error("[batch] %s exception: %s", code, e)
                results[code] = {'price': 0, 'change': 0, 'source': 'error', 'elapsed': 0}

    total_time = time.time() - t_start
    ok_count = sum(1 for r in results.values() if r.get('price', 0) > 0)
    _log.info("[batch] done: %d/%d ok in %.1fs", ok_count, len(results), total_time)

    # 输出摘要 (logging避免stdout冲突)
    source_counts = {}
    for r in results.values():
        s = r.get('source', 'unknown')
        source_counts[s] = source_counts.get(s, 0) + 1
    src_summary = ', '.join(f"{s}({c})" for s, c in sorted(source_counts.items()))
    _log.info("[batch] sources: %s", src_summary)
    try:
        print(f"\n  done: {ok_count}/{len(results)} ok ({total_time:.1f}s) [{src_summary}]")
    except Exception:
        pass

    return results


def get_stats() -> Dict:
    """获取本次运行的数据源统计 (线程安全)"""
    with _stats_lock:
        return dict(_stats)


def reset_stats():
    """重置统计 (线程安全)"""
    with _stats_lock:
        for k in _stats:
            _stats[k] = 0.0 if k == 'total_elapsed' else 0


# ============================================================
# 兼容旧接口 (供 daily_report.py 直接替换)
# ============================================================

def get_stock_price(code: str) -> Dict:
    """兼容旧接口: 获取股票价格"""
    return get_quote(code, is_fund=False)


def get_fund_price(code: str) -> Dict:
    """兼容旧接口: 获取基金价格"""
    return get_quote(code, is_fund=True)


# ---- 快速测试 ----
if __name__ == '__main__':
    import yaml

    config_path = os.path.join(os.path.dirname(__file__), 'config', 'portfolio.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        assets = yaml.safe_load(f)['assets']

    stocks = [a['code'] for a in assets if not a['code'].startswith('5')]
    funds = [a['code'] for a in assets if a['code'].startswith('5')]

    print("=" * 70)
    print("统一数据提供层 — Wind / iFinD / 免费数据源多级回退测试")
    print("=" * 70)

    results = get_quotes_batch(stocks, funds, max_workers=5)

    print(f"\n{'名称':<12} {'代码':<10} {'价格':>10} {'涨跌':>8} {'来源':<16} {'耗时':>5s}")
    print("-" * 70)

    names = {a['code']: a['name'] for a in assets}
    for a in assets:
        code = a['code']
        r = results.get(code, {})
        price = r.get('price', 0)
        chg = r.get('change', 0)
        src = r.get('source', '?')
        el = r.get('elapsed', 0)

        status = "✅" if price > 0 else "❌"
        src_icon = {
            'wind_analytics': '☁️分析',
            'wind_direct': '⚡直连',
            'ifind': '📡iFinD',
            'akshare': '📊akshare',
            'tushare': '📈tushare',
            'baostock': '📉baostock',
            'efinance': '💰efinance',
            'yahoo_finance': '🌍yahoo',
            'pandas_datareader': '📚pdr',
            'sina': '🌐新浪',
            'local_cache': '💾缓存',
            'fallback': '📌兜底',
            'failed': '❌失败',
            'error': '💥异常'
        }.get(src, src)

        print(f"{status} {names[code]:<10} {code:<10} ¥{price:>9.2f} {chg:>+7.2f}%  {src_icon:<14} {el:>4.1f}")

    print("\n" + "=" * 70)
    print("统计:", json.dumps(get_stats(), indent=2))
    print("=" * 70)
