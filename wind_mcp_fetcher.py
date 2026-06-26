# -*- coding: utf-8 -*-
"""
Wind MCP 统一数据获取器 — 全局数据源优先级第1位

提供可复用的 Wind MCP 数据获取函数，所有 E:\各种PY程序 内的模块
应优先调用本模块，仅在 Wind 不可用时回退到其他数据源。

支持功能:
  - 单只行情查询 (股票/ETF/基金/指数)
  - 批量行情查询 (并发)
  - K线历史数据
  - 基金净值/规模数据

数据源优先级（全局统一）:
  1. Wind MCP (本模块) ← 最高优先
  2. iFinD MCP
  3. AKShare / eFinance
  4. BaoStock / Tushare
  5. 新浪财经 / yfinance / pandas_datareader

使用方式:
    from wind_mcp_fetcher import wind_get_quote, wind_get_batch_quotes
    
    # 单只查询
    quote = wind_get_quote('588000', is_fund=True)
    # => {'price': 1.794, 'change': -0.5, 'volume': 29058300, 'source': 'wind_mcp'}
    
    # 批量查询
    quotes = wind_get_batch_quotes(['588000', '159915', '510300'], is_fund=True)
    # => {'588000': {'price': 1.794, ...}, '159915': {...}, ...}
"""

import json
import os
import subprocess
import time
import logging
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---- 配置 ----
WIND_SKILL_DIR = r'C:\Users\Administrator\.agents\skills\wind-mcp-skill'
WIND_CLI = os.path.join(WIND_SKILL_DIR, 'scripts', 'cli.mjs')
WIND_API_KEY = os.environ.get('WIND_API_KEY', '')
WIND_TIMEOUT = 20  # 单次调用超时(秒)
MAX_CONCURRENT = 3  # 最大并发数(避免触发限流)

# ---- 日志 ----
logger = logging.getLogger('wind_mcp')


def _build_env() -> Dict[str, str]:
    """构建带 API Key 的环境变量"""
    env = os.environ.copy()
    if not env.get('WIND_API_KEY'):
        env['WIND_API_KEY'] = WIND_API_KEY
    return env


def _code_to_windcode(code: str, is_fund: bool = False) -> str:
    """
    将A股代码转换为Wind格式
    
    Args:
        code: 6位代码，如 '588000', '600519'
        is_fund: 是否为基金/ETF
    
    Returns:
        Wind代码，如 '588000.SH', '000001.SZ'
    """
    code = str(code).strip()
    # 去除已有后缀
    for suffix in ('.SH', '.SZ', '.SS'):
        code = code.upper().replace(suffix, '')
    
    if is_fund or code.startswith(('51', '58', '15')):
        # 上交所 ETF/基金
        return f"{code}.SH"
    elif code.startswith(('00', '30')):
        # 深交所
        return f"{code}.SZ"
    elif code.startswith(('6',)):
        # 上交所股票
        return f"{code}.SH"
    elif code.startswith(('4', '8')):
        # 北交所
        return f"{code}.BJ"
    else:
        # 默认按上交所处理
        return f"{code}.SH"


def _call_wind_cli(server_type: str, tool_name: str, params: dict) -> Optional[Any]:
    """
    调用 Wind CLI 并解析返回结果
    
    Args:
        server_type: 如 'fund_data', 'stock_data', 'index_data'
        tool_name: 如 'get_fund_quote', 'get_stock_quote'
        params: 参数字典
    
    Returns:
        解析后的数据字典，失败返回 None
    """
    try:
        cmd = ['node', WIND_CLI, 'call', server_type, tool_name, json.dumps(params)]
        result = subprocess.run(
            cmd,
            cwd=WIND_SKILL_DIR,
            capture_output=True,
            text=True,
            timeout=WIND_TIMEOUT,
            env=_build_env(),
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            logger.debug("[wind_cli] %s/%s rc=%d", server_type, tool_name, result.returncode)
            return None
        
        data = json.loads(result.stdout)
        
        # 检查错误
        if not data.get('ok', True):
            err = data.get('error', {})
            logger.debug("[wind_cli] %s/%s error=%s", server_type, tool_name, 
                       err.get('code', 'unknown'))
            return None
        
        content_list = data.get('content', [])
        if not content_list:
            return None
        
        text = content_list[0].get('text', '')
        if not text:
            return None
        
        return json.loads(text)
        
    except subprocess.TimeoutExpired:
        logger.warning("[wind_cli] %s/%s 超时(%ds)", server_type, tool_name, WIND_TIMEOUT)
    except json.JSONDecodeError as e:
        logger.debug("[wind_cli] %s/%s JSON解析失败: %s", server_type, tool_name, e)
    except Exception as e:
        logger.debug("[wind_cli] %s/%s 异常: %s", server_type, tool_name, e)
    
    return None


def _parse_quote_from_response(quote_data: dict) -> Optional[Dict]:
    """
    从Wind响应中解析最新价格
    
    支持多种返回格式:
      格式1: {data: {rows: [[match, avgprice, volume, ...], ...]}, ...}  <- get_fund_quote/get_stock_quote
      格式2: {datas: [[open, close, volume, ...], ...]}                  <- 备选分钟线
      格式3: {close: 1.794, last_price: 1.794, ...}                    <- 指标类
    """
    if not quote_data:
        return None
    
    price = None
    change = None
    volume = None
    
    # 格式1: data.rows (get_fund_quote / get_stock_quote 实际返回)
    if 'data' in quote_data and isinstance(quote_data['data'], dict):
        inner = quote_data['data']
        rows = inner.get('rows', [])
        if rows and isinstance(rows, list) and len(rows) > 0:
            last_row = rows[-1]
            if isinstance(last_row, list) and len(last_row) >= 2:
                try:
                    price = float(last_row[1])  # index=1=AVGPRICE(收盘价)
                    volume = float(last_row[2]) if len(last_row) > 2 else None
                except (ValueError, TypeError):
                    pass
    
    # 格式2: datas 数组
    if price is None and 'datas' in quote_data and isinstance(quote_data['datas'], list):
        rows = quote_data['datas']
        if rows and isinstance(rows[-1], list) and len(rows[-1]) >= 2:
            try:
                price = float(rows[-1][1])
            except (ValueError, TypeError):
                pass
    
    # 格式3: 顶层字段
    if price is None:
        for field in ('close', 'last_price', 'price', 'latest_price', '最新成交价'):
            if field in quote_data:
                try:
                    p = float(quote_data[field])
                    if p > 0:
                        price = p
                        break
                except (ValueError, TypeError):
                    continue
    
    # 尝试提取涨跌幅
    if 'data' in quote_data and isinstance(quote_data['data'], dict):
        inner = quote_data['data']
        rows = inner.get('rows', [])
        if rows and isinstance(rows, list) and len(rows) > 0:
            last_row = rows[-1]
            if isinstance(last_row, list) and len(last_row) > 3:
                # 尝试从倒数第二行计算涨跌幅
                if len(rows) >= 2:
                    prev_row = rows[-2]
                    if isinstance(prev_row, list) and len(prev_row) >= 2:
                        try:
                            prev_p = float(prev_row[1])
                            curr_p = float(last_row[1])
                            if prev_p > 0:
                                change = round((curr_p - prev_p) / prev_p * 100, 2)
                        except (ValueError, TypeError):
                            pass
    
    if price is not None and price > 0:
        result = {
            'price': round(price, 3),
            'source': 'wind_mcp',
        }
        if change is not None:
            result['change'] = change
        if volume is not None:
            result['volume'] = int(volume) if volume == int(volume) else round(volume, 0)
        return result
    
    return None


def wind_get_quote(code: str, is_fund: bool = False) -> Optional[Dict]:
    """
    获取单只标的实时行情 (Wind MCP)
    
    Args:
        code: 6位代码，如 '588000'(科创50ETF), '600519'(贵州茅台)
        is_fund: 是否为基金/ETF (默认自动判断)
    
    Returns:
        成功: {'price': 1.794, 'change': -0.5, 'volume': 29058300, 'source': 'wind_mcp'}
        失败: None
    """
    windcode = _code_to_windcode(code, is_fund)
    
    # 根据类型选择server和tool
    if is_fund or code.startswith(('51', '58', '15', '16')):
        server_type = 'fund_data'
        tool_name = 'get_fund_quote'
    elif code.startswith(('000', '399', '0003', '0009')):
        # 指数
        server_type = 'index_data'
        tool_name = 'get_index_quote'
    else:
        server_type = 'stock_data'
        tool_name = 'get_stock_quote'
    
    params = {"windcode": windcode}
    t0 = time.time()
    
    response = _call_wind_cli(server_type, tool_name, params)
    result = _parse_quote_from_response(response)
    
    elapsed = time.time() - t0
    if result:
        result['windcode'] = windcode
        result['elapsed'] = round(elapsed, 2)
        logger.info("[wind_quote] %s => %.3f (%.2fs)", windcode, result['price'], elapsed)
    else:
        logger.debug("[wind_quote] %s 无结果 (%.2fs)", windcode, elapsed)
    
    return result


def wind_get_batch_quotes(
    codes: List[str],
    is_fund: bool = False,
    max_concurrent: int = MAX_CONCURRENT
) -> Dict[str, Dict]:
    """
    批量获取多只标的实时行情 (Wind MCP 并发)
    
    Args:
        codes: 代码列表，如 ['588000', '159915', '510300']
        is_fund: 是否全部为基金/ETF
        max_concurrent: 最大并发数
    
    Returns:
        {code: {'price': ..., 'change': ..., 'source': 'wind_mcp'}, ...}
    """
    results = {}
    
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        future_to_code = {
            executor.submit(wind_get_quote, code, is_fund): code
            for code in codes
        }
        
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            try:
                result = future.result(timeout=WIND_TIMEOUT + 5)
                if result:
                    results[code] = result
            except Exception as e:
                logger.debug("[wind_batch] %s 异常: %s", code, e)
    
    logger.info("[wind_batch] %d/%d 成功 (%.2fs)", 
               len(results), len(codes), time.time() - (time.time() - 0))
    return results


def wind_get_kline(
    code: str,
    days: int = 30,
    is_fund: bool = False
) -> Optional[List[Dict]]:
    """
    获取K线历史数据 (Wind MCP)
    
    Args:
        code: 6位代码
        days: 天数
        is_fund: 是否基金
    
    Returns:
        [{'date': '20260612', 'open': 1.80, 'close': 1.79, 'high': 1.81, 'low': 1.78, 'volume': 29058300}, ...]
    """
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    windcode = _code_to_windcode(code, is_fund)
    
    if is_fund or code.startswith(('51', '58', '15')):
        server_type = 'fund_data'
        tool_name = 'get_fund_kline'
    else:
        server_type = 'stock_data'
        tool_name = 'get_stock_kline'
    
    params = {
        "windcode": windcode,
        "begin_date": start_date,
        "end_date": end_date,
    }
    
    response = _call_wind_cli(server_type, tool_name, params)
    if not response:
        return None
    
    # 解析K线数据
    klines = []
    if 'data' in response and isinstance(response['data'], dict):
        rows = response['data'].get('rows', [])
        columns = [c['name'].lower() for c in response['data'].get('columns', [])]
        
        for row in rows:
            if not isinstance(row, list):
                continue
            item = {}
            for i, col in enumerate(columns):
                if i < len(row):
                    item[col] = row[i]
            
            klines.append(item)
    
    if klines:
        logger.info("[wind_kline] %s %d条 [%s~%s]", windcode, len(klines), start_date, end_date)
    
    return klines if klines else None


def wind_check_connection() -> Dict[str, Any]:
    """
    检查 Wind MCP 连接状态
    
    Returns:
        {'connected': bool, 'api_key_set': bool, 'latency_ms': float, 'test_code': str}
    """
    result = {
        'api_key_set': bool(os.environ.get('WIND_API_KEY') or WIND_API_KEY),
        'connected': False,
        'latency_ms': -1,
        'test_code': '',
    }
    
    t0 = time.time()
    # 用一个流动性好的ETF测试
    test_resp = wind_get_quote('510300', is_fund=True)  # 沪深300ETF
    elapsed = (time.time() - t0) * 1000
    
    result['latency_ms'] = round(elapsed, 0)
    result['connected'] = test_resp is not None
    result['test_price'] = test_resp.get('price') if test_resp else None
    
    return result


# ---- 快捷导出 ----
__all__ = [
    'wind_get_quote',
    'wind_get_batch_quotes',
    'wind_get_kline',
    'wind_check_connection',
    '_code_to_windcode',
]
