# -*- coding: utf-8 -*-
"""Wind MCP 数据获取工具函数

提供 Wind MCP CLI 调用封装，包括：
- 代理绕过（解决国内代理环境下金融 API 被拒绝的问题）
- Wind 标准代码格式转换
- K线数据获取
- 实时行情快照获取
- 组合目标约束常量
"""
from __future__ import annotations

import os
import sys
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

# ============================================================
# 代理绕过：系统代理(127.0.0.1:7897)拒绝转发部分金融API域名
# 在导入任何使用requests的模块之前设置，令urllib3直连
# ============================================================
_FINANCE_NO_PROXY_DOMAINS = (
    'push2his.eastmoney.com,push2.eastmoney.com,'
    'query1.finance.yahoo.com,query2.finance.yahoo.com,fc.yahoo.com,'
    'eastmoney.com,finance.yahoo.com'
)
_existing_no_proxy = os.environ.get('NO_PROXY', '')
_sep = ',' if _existing_no_proxy else ''
os.environ['NO_PROXY'] = _existing_no_proxy + _sep + _FINANCE_NO_PROXY_DOMAINS
os.environ['no_proxy'] = os.environ['NO_PROXY']

# Wind MCP 技能目录
try:
    from utils.paths import get_wind_skill_dir
    WIND_MCP_SKILL_DIR = get_wind_skill_dir()
except ImportError:
    WIND_MCP_SKILL_DIR = r'C:\Users\Administrator\.agents\skills\wind-mcp-skill'

# 基础目录（供 .env 文件查找）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 日志
try:
    from utils.logging_manager import get_logger
    logger = get_logger('wind_mcp')
except ImportError:
    import logging
    logger = logging.getLogger('wind_mcp')


def _wind_code(code: str) -> str:
    """A股/ETF代码 -> Wind标准格式"""
    # 上海交易所: 主板60xxxx, 科创板688xxx, ETF 51xxxx/58xxxx
    if code.startswith(('51', '58', '60', '68')):
        return f"{code}.SH"
    else:
        return f"{code}.SZ"


def _wind_mcp_call(server_type: str, tool_name: str, params: dict, timeout: int = 20) -> Optional[dict]:
    """调用 Wind MCP CLI，返回解析后的 data dict，失败返回 None。

    Wind MCP 返回格式：
    {"content":[{"type":"text","text":"{\"data\":{...},\"error\":null}"}],"isError":false}
    本函数提取并解析 data 字段。
    """
    try:
        wind_env = os.environ.copy()
        if not wind_env.get('WIND_API_KEY'):
            # P0 修复: API Key 硬编码 → 环境变量/.env 文件; 生产环境必须配置
            _env_path = os.path.join(_BASE_DIR, '.env')
            _env_key = ''
            if os.path.exists(_env_path):
                with open(_env_path, 'r', encoding='utf-8') as _f:
                    for _line in _f:
                        _line = _line.strip()
                        if _line.startswith('#') or not _line or '=' not in _line:
                            continue
                        _k, _v = _line.split('=', 1)
                        if _k.strip() == 'WIND_API_KEY':
                            _env_key = _v.strip()
            if _env_key:
                wind_env['WIND_API_KEY'] = _env_key
            else:
                # 最终兜底：仅用于开发/测试环境
                wind_env['WIND_API_KEY'] = os.environ.get(
                    'WIND_API_KEY',
                    os.environ.get('QUANT_WIND_KEY', 'PLACEHOLDER_USE_ENV_OR_DOTENV')
                )
                if 'PLACEHOLDER' in wind_env['WIND_API_KEY']:
                    print("⚠️ 警告: 未配置 WIND_API_KEY，请设置环境变量 export WIND_API_KEY=<your-key> 或在 .env 文件中配置")
        result = subprocess.run(
            ['node', 'scripts/cli.mjs', 'call', server_type, tool_name,
             json.dumps(params, ensure_ascii=False)],
            cwd=WIND_MCP_SKILL_DIR, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=timeout, env=wind_env
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        stdout = result.stdout.strip()
        # 过滤 PowerShell CLIXML 噪声行
        if '\n' in stdout and '#< CLIXML' in stdout:
            stdout = stdout.split('\n')[0]
        outer = json.loads(stdout)
        if outer.get('isError'):
            return None
        text = (outer.get('content', [{}])[0] or {}).get('text', '')
        if not text:
            return None
        inner = json.loads(text)
        if inner.get('error'):
            return None
        return inner.get('data')
    except Exception:
        return None


def _wind_mcp_fetch_kline(code: str, begin_date: str, end_date: str) -> Optional['pd.DataFrame']:
    """从 Wind MCP 获取 A股/ETF 日K线，返回 DataFrame（列: open/high/low/close/volume）。

    Wind K线列顺序: TIME, OPEN, MATCH(收盘), HIGH, LOW, TURNOVER, VOLUME, CHANGEHANDRATE, AVPRICE, _DATE
    """
    import pandas as _wk_pd
    windcode = _wind_code(code)

    # 判断 ETF vs 股票，选择正确的 server/tool
    if code.startswith(('51', '58', '159', '16', '588', '560', '561', '562', '563', '512', '513')):
        server, tool = 'fund_data', 'get_fund_kline'
    else:
        server, tool = 'stock_data', 'get_stock_kline'

    # Wind MCP 要求日期格式为 yyyyMMdd（无分隔符）
    _bgn = begin_date.replace('-', '')
    _end = end_date.replace('-', '')
    kdata = _wind_mcp_call(server, tool, {
        "windcode": windcode,
        "begin_date": _bgn,
        "end_date": _end,
        "period": "10",       # 日K
        "aftime": "0",        # 前复权
    })
    if not kdata:
        return None

    columns = [c['name'] for c in kdata.get('columns', [])]
    rows = kdata.get('rows', [])
    if not rows:
        return None

    # 列索引查找
    col_map = {c: i for i, c in enumerate(columns)}
    try:
        result = []
        for row in rows:
            result.append({
                'date': row[col_map.get('TIME', 0)][:10] if row[col_map.get('TIME', 0)] else None,
                'open': float(row[col_map['OPEN']]),
                'close': float(row[col_map['MATCH']]),
                'high': float(row[col_map['HIGH']]),
                'low': float(row[col_map['LOW']]),
                'volume': float(row[col_map['VOLUME']]),
            })
        df = _wk_pd.DataFrame(result)
        df['date'] = _wk_pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        df = df.dropna()
        if len(df) >= 10:
            return df
    except (KeyError, IndexError, ValueError):
        pass
    return None


def _wind_mcp_fetch_quote(code: str) -> Optional[dict]:
    """从 Wind MCP 获取单只标的实时行情快照，返回 dict {name, price, change_pct, ...} 或 None"""
    windcode = _wind_code(code)
    if code.startswith(('51', '58', '159', '16', '588', '560', '561', '562', '563', '512', '513')):
        server, tool = 'fund_data', 'get_fund_price_indicators'
    else:
        server, tool = 'stock_data', 'get_stock_price_indicators'

    data = _wind_mcp_call(server, tool, {
        "windcode": windcode,
        "indexes": "中文简称,最新成交价,涨跌幅,今日开盘价,今日最高价,今日最低价,成交量,成交额"
    })
    if not data:
        return None
    columns = [c['name'] for c in data.get('columns', [])]
    rows = data.get('rows', [])
    if not rows or not rows[0]:
        return None
    row = rows[0]
    col_map = {c: i for i, c in enumerate(columns)}
    try:
        price = float(row[col_map.get('最新成交价', 1)]) if '最新成交价' in col_map else 0
        if price <= 0 or price > 1e6:
            return None  # 非交易时间 Wind 返回 INVALID
        return {
            'name': row[col_map.get('中文简称', 0)] if '中文简称' in col_map else code,
            'price': price,
            'change_pct': float(row[col_map.get('涨跌幅', 2)]) if '涨跌幅' in col_map else 0,
            'volume': float(row[col_map.get('成交量', 6)]) if '成交量' in col_map else 0,
            'source': 'Wind MCP'
        }
    except (ValueError, IndexError, KeyError):
        return None


# ============================================================
# 期货/期权数据获取
# ============================================================

def _wind_futures_code(symbol: str, exchange: str = "SHF") -> str:
    """构建Wind期货代码, 如 CU + SHF → CU2506.SHF"""
    from datetime import datetime
    now = datetime.now()
    m = (now.month + 1) % 12 + 1
    y = now.year
    if m == 1:
        y += 1
    month = f"{y % 100:02d}{m:02d}"
    exchange_map = {"SHF": "SHF", "DCE": "DCE", "ZCE": "ZCE", "CFFEX": "CFE", "INE": "INE"}
    exch = exchange_map.get(exchange, exchange)
    return f"{symbol}{month}.{exch}"


def wind_fetch_futures_quote(symbol: str, exchange: str = "SHF") -> Optional[dict]:
    """通过Wind MCP获取期货实时行情快照"""
    windcode = _wind_futures_code(symbol, exchange)

    # 尝试 futures_data 接口
    data = _wind_mcp_call('futures_data', 'get_futures_quote', {
        "windcode": windcode,
        "indicators": "最新成交价,涨跌幅,成交量,持仓量,开盘价,最高价,最低价,昨结算"
    }, timeout=15)
    if data:
        try:
            columns = [c['name'] for c in data.get('columns', [])]
            rows = data.get('rows', [])
            if rows and rows[0]:
                row = rows[0]
                col_map = {c: i for i, c in enumerate(columns)}
                price = _safe_f(row, col_map, ['最新成交价'])
                if price and price > 0:
                    return {
                        'price': price,
                        'change_pct': _safe_f(row, col_map, ['涨跌幅']),
                        'volume': _safe_f(row, col_map, ['成交量']),
                        'open_interest': _safe_f(row, col_map, ['持仓量']),
                        'open': _safe_f(row, col_map, ['开盘价'], price),
                        'high': _safe_f(row, col_map, ['最高价'], price),
                        'low': _safe_f(row, col_map, ['最低价'], price),
                        'settlement': _safe_f(row, col_map, ['昨结算'], price),
                        'source': 'wind_futures',
                    }
        except Exception:
            pass
    return None


def wind_fetch_futures_batch(symbols: List[str], exchange: str = "SHF", max_workers: int = 6) -> Dict[str, dict]:
    """批量获取期货行情 — 并行化"""
    results = {}

    def _fetch_one(sym):
        r = wind_fetch_futures_quote(sym, exchange)
        if r:
            return (sym, r)
        for exch in ["DCE", "ZCE", "CFFEX"]:
            if exch == exchange:
                continue
            r2 = wind_fetch_futures_quote(sym, exch)
            if r2:
                return (sym, r2)
        return (sym, None)

    with ThreadPoolExecutor(max_workers=min(max_workers, len(symbols))) as pool:
        futures = {pool.submit(_fetch_one, s): s for s in symbols}
        for f in as_completed(futures):
            sym, result = f.result()
            if result:
                results[sym] = result
    return results


def wind_fetch_options_chain(underlying: str, option_type: str = "all") -> Optional[dict]:
    """通过Wind MCP获取期权链数据"""
    # 510300 → 510300.SH (ETF期权在SHF)
    windcode = f"{underlying}.SH" if underlying.startswith(('51', '58')) else f"{underlying}.SZ"
    data = _wind_mcp_call('options_data', 'get_options_chain', {
        "windcode": windcode,
        "option_type": option_type,
        "indicators": "最新成交价,隐含波动率,Delta,Gamma,Theta,Vega,成交量"
    }, timeout=15)
    if data:
        return data
    # 回退到analytics
    data = _wind_mcp_call('analytics_data', 'get_financial_data', {
        "question": f"查询{underlying}的期权链隐含波动率、PCR和最大痛点"
    }, timeout=20)
    return data


def _safe_f(row, col_map, keys, default=0.0):
    """安全提取浮点数 (列匹配)"""
    for k in keys:
        idx = col_map.get(k)
        if idx is not None and idx < len(row) and row[idx] is not None:
            try:
                return float(row[idx])
            except (ValueError, TypeError):
                continue
    return default


def get_realtime_prices_batch(codes: List[str], max_workers: int = 8) -> Dict[str, float]:
    """并行获取多个标的的实时价格，返回 {code: price}"""
    results = {}

    def _fetch_price(code):
        p = get_realtime_price(code)
        return (code, p)

    with ThreadPoolExecutor(max_workers=min(max_workers, max(1, len(codes)))) as pool:
        futures = {pool.submit(_fetch_price, c): c for c in codes}
        for f in as_completed(futures):
            code, price = f.result()
            if price and 0 < price < 10000:
                results[code] = price
    return results


def get_realtime_price(code: str) -> Optional[float]:
    """单只标的实时价格，返回 float 或 None"""
    quote = _wind_mcp_fetch_quote(code)
    if quote:
        return quote.get('price')
    return None


# ============================================================
# 五年持仓目标约束（硬门槛 — 所有策略须在回测/滚动中同时满足）
# ============================================================
PORTFOLIO_TARGETS: Dict[str, float] = {
    'annual_return': 0.08,    # 年化收益率 ≥ 8%
    'max_drawdown': -0.15,    # 最大回撤 ≥ -15%（即回撤 ≤ 15%）
    'years': 5.0,             # 持有期 = 5 年（用于年化口径统一 + 滚动检验）
    'min_cagr_5y': 0.08,      # 5 年滚动复合年化仍须 ≥ 8%
    'max_dd_any_year': -0.15, # 任何单一年的最大回撤 ≤ 15%
}
