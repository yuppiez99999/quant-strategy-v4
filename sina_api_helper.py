# -*- coding: utf-8 -*-
"""
行情数据获取模块 — Wind MCP优先 + iFinD MCP回退 + 新浪财经兜底

数据源优先级 (全局统一):
  1. Wind MCP (最高优先 — 稳定、权威、实时)
  2. iFinD MCP (备用 — 同花顺金融终端)
  3. 新浪财经 API (免费兜底)

接口说明:
- Wind MCP: 通过 wind_mcp_fetcher 调用万得金融终端
- 新浪财经实时行情接口: https://hq.sinajs.cn/list=shXXX/szXXX
- 返回格式: var hq_str_shXXX="股票名称,最新价,涨跌额,涨跌幅,..."

使用方式:
    from sina_api_helper import get_price, get_kline_latest, get_batch_prices
    price = get_price('601088')          # Wind优先，新浪回退
    result = get_kline_latest('002371')
    prices = get_batch_prices(['601088','600995'])
"""

import requests
import time
import logging
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---- Wind MCP 前置层 ----
_WIND_MCP_AVAILABLE = None  # 延迟检测


def _try_wind_mcp() -> bool:
    """检测Wind MCP是否可用"""
    global _WIND_MCP_AVAILABLE
    if _WIND_MCP_AVAILABLE is not None:
        return _WIND_MCP_AVAILABLE
    try:
        import sys
        import os
        # 添加策略目录到路径
        strat_dir = os.path.dirname(os.path.abspath(__file__))
        if strat_dir not in sys.path:
            sys.path.insert(0, strat_dir)
        from wind_mcp_fetcher import wind_get_quote
        test = wind_get_quote('510300', is_fund=True)
        _WIND_MCP_AVAILABLE = test is not None and test.get('price', 0) > 0
    except Exception:
        _WIND_MCP_AVAILABLE = False
    return _WIND_MCP_AVAILABLE


def _wind_code_from_symbol(symbol: str) -> str:
    """将sh/sz前缀代码转为6位纯代码"""
    s = symbol.lower().strip()
    for prefix in ('sh', 'sz', 'sh', 'sz'):
        if s.startswith(prefix):
            return s[len(prefix):]
    return s


def get_price(symbol: str) -> Optional[float]:
    """
    获取实时价格 (Wind MCP优先 → 新浪回退)
    
    Args:
        symbol: 股票/ETF代码（支持 sh601088 / 601088 两种格式）
    
    Returns:
        当前价格(float)，失败返回 None
    """
    code = _wind_code_from_symbol(symbol)
    is_fund = code.startswith(('51', '58', '15'))

    # 优先尝试 Wind MCP
    if _try_wind_mcp():
        try:
            from wind_mcp_fetcher import wind_get_quote
            result = wind_get_quote(code, is_fund=is_fund)
            if result and result.get('price', 0) > 0:
                logger.info("[wind_mcp] %s => %.3f", symbol, result['price'])
                return result['price']
        except Exception as e:
            logger.debug("[wind_mcp] %s fallback to sina: %s", symbol, e)

    # 回退到新浪财经
    return get_sina_price(symbol)


def get_kline_latest(symbol: str) -> Optional[Dict]:
    """
    获取最新行情数据 (Wind MCP优先 → 新浪回退)
    
    Args:
        symbol: 股票/ETF代码
    
    Returns:
        {'name': str, 'price': float, 'change': float, 'open/high/low/volume/amount': ...}
    """
    code = _wind_code_from_symbol(symbol)
    is_fund = code.startswith(('51', '58', '15'))

    # 优先尝试 Wind MCP
    if _try_wind_mcp():
        try:
            from wind_mcp_fetcher import wind_get_quote
            result = wind_get_quote(code, is_fund=is_fund)
            if result and result.get('price', 0) > 0:
                return {
                    'name': symbol,
                    'price': result['price'],
                    'change': result.get('change', 0),
                    'open': 0,
                    'high': 0,
                    'low': 0,
                    'volume': result.get('volume', 0),
                    'amount': 0,
                    'source': 'wind_mcp',
                }
        except Exception as e:
            logger.debug("[wind_mcp] %s fallback to sina: %s", symbol, e)

    # 回退到新浪财经
    return get_sina_kline_latest(symbol)


def get_batch_prices(symbols: list) -> Dict[str, Optional[Dict]]:
    """
    批量获取行情 (Wind MCP批量优先 → 新浪逐个回退)
    
    Args:
        symbols: 代码列表（支持 sh601088 / 601088 格式）
    
    Returns:
        {symbol: Dict or None}
    """
    codes = [_wind_code_from_symbol(s) for s in symbols]
    results = {}

    # Wind MCP 批量获取
    if _try_wind_mcp():
        try:
            from wind_mcp_fetcher import wind_get_batch_quotes
            fund_codes = [c for c in codes if c.startswith(('51', '58', '15'))]
            stock_codes = [c for c in codes if c not in fund_codes]
            
            if stock_codes:
                sr = wind_get_batch_quotes(stock_codes, is_fund=False)
                for c, r in sr.items():
                    for sym in symbols:
                        if _wind_code_from_symbol(sym) == c:
                            results[sym] = {**r, 'name': sym, 'source': 'wind_mcp'}
                            break
            if fund_codes:
                fr = wind_get_batch_quotes(fund_codes, is_fund=True)
                for c, r in fr.items():
                    for sym in symbols:
                        if _wind_code_from_symbol(sym) == c:
                            results[sym] = {**r, 'name': sym, 'source': 'wind_mcp'}
                            break
            
            logger.info("[batch_wind] got %d/%d via wind_mcp", len(results), len(symbols))
        except Exception as e:
            logger.debug("[batch_wind] err: %s, fallback to sina", e)

    # 对未获取到的用新浪补齐
    remaining = [s for s in symbols if s not in results]
    if remaining:
        sina_results = batch_get_sina_prices(remaining)
        results.update(sina_results)

    return results

# 新浪财经接口URL模板
SINA_HQ_URL = 'https://hq.sinajs.cn/list={}'

# 请求超时时间
TIMEOUT = 10

# 请求间隔（避免被限流）
REQUEST_INTERVAL = 0.1

# 请求头（模拟浏览器）
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://finance.sina.com.cn/',
    'Connection': 'keep-alive',
}

# 日志配置
logger = logging.getLogger('sina_api')
logger.setLevel(logging.DEBUG)


def _create_session() -> requests.Session:
    """创建配置好的请求会话"""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.timeout = TIMEOUT
    return session


def get_sina_price(symbol: str) -> Optional[float]:
    """
    获取新浪财经实时价格
    
    Args:
        symbol: 股票代码（带市场前缀，如 sh601088, sz002371）
    
    Returns:
        当前价格，如果获取失败返回 None
    """
    try:
        session = _create_session()
        url = SINA_HQ_URL.format(symbol)
        response = session.get(url)
        response.encoding = 'gbk'
        data = response.text
        
        logger.debug(f"Response for {symbol}: {data[:100]}...")
        
        if 'var hq_str_' in data:
            parts = data.split(',')
            if len(parts) > 3:
                # 第2个字段是最新价（索引1）
                price_str = parts[1].strip()
                if price_str:
                    return float(price_str)
        else:
            logger.debug(f"Unexpected response format for {symbol}")
    except requests.exceptions.RequestException as e:
        logger.debug(f"Request failed for {symbol}: {e}")
    except Exception as e:
        logger.debug(f"Parse failed for {symbol}: {e}")
    
    return None


def get_sina_kline_latest(symbol: str) -> Optional[Dict]:
    """
    获取新浪财经最新行情数据（包含价格和涨跌幅）
    
    Args:
        symbol: 股票代码（带市场前缀，如 sh601088, sz002371）
    
    Returns:
        包含 price 和 change 的字典，如果获取失败返回 None
    """
    try:
        session = _create_session()
        url = SINA_HQ_URL.format(symbol)
        response = session.get(url)
        response.encoding = 'gbk'
        data = response.text
        
        logger.debug(f"Response length for {symbol}: {len(data)} chars")
        
        if 'var hq_str_' in data:
            parts = data.split(',')
            if len(parts) >= 4:
                # 解析字段
                name = parts[0].split('_')[-1] if '_' in parts[0] else ''
                price = float(parts[1].strip()) if parts[1].strip() else 0.0
                change = float(parts[3].strip()) if parts[3].strip() else 0.0
                
                if price > 0:
                    result = {
                        'name': name,
                        'price': price,
                        'change': change,
                        'open': float(parts[4].strip()) if len(parts) > 4 else 0.0,
                        'high': float(parts[5].strip()) if len(parts) > 5 else 0.0,
                        'low': float(parts[6].strip()) if len(parts) > 6 else 0.0,
                        'volume': int(float(parts[8].strip())) if len(parts) > 8 else 0,
                        'amount': float(parts[9].strip()) if len(parts) > 9 else 0.0,
                    }
                    logger.info(f"SINA API success: {symbol} price={price:.2f}")
                    return result
            else:
                logger.debug(f"Insufficient data parts for {symbol}: {len(parts)}")
        else:
            logger.debug(f"Response does not contain hq_str_: {data[:50]}")
    except requests.exceptions.RequestException as e:
        logger.debug(f"Request exception for {symbol}: {e}")
    except ValueError as e:
        logger.debug(f"Parse error for {symbol}: {e}")
    except Exception as e:
        logger.debug(f"Unexpected error for {symbol}: {e}")
    
    return None


def batch_get_sina_prices(symbols: list) -> Dict[str, Optional[Dict]]:
    """批量获取新浪财经行情数据 (并行化)"""
    results = {}

    def _fetch_one(symbol):
        return (symbol, get_sina_kline_latest(symbol))

    with ThreadPoolExecutor(max_workers=min(8, len(symbols))) as pool:
        futures = {pool.submit(_fetch_one, s): s for s in symbols}
        for f in as_completed(futures):
            symbol, result = f.result()
            results[symbol] = result

    return results


if __name__ == '__main__':
    # 测试
    test_codes = ['sh601088', 'sz002371', 'sh518880']
    
    print("测试新浪财经API:")
    print("-" * 50)
    
    for code in test_codes:
        result = get_sina_kline_latest(code)
        if result:
            print(f"{code}:")
            print(f"  名称: {result['name']}")
            print(f"  价格: {result['price']:.2f}")
            print(f"  涨跌幅: {result['change']:.2f}%")
            print(f"  开盘: {result['open']:.2f}")
            print(f"  最高: {result['high']:.2f}")
            print(f"  最低: {result['low']:.2f}")
        else:
            print(f"{code}: 获取失败")
        print()
    
    print("-" * 50)
    print("测试完成")