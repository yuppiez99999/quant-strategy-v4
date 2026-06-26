# -*- coding: utf-8 -*-
"""
统一数据源连接器注册模块 — Wind MCP / iFinD MCP / AKShare / Sina / 本地缓存

将 wind_mcp_fetcher 和 ifind_client 封装为 DataConnector 子类，注册到
DataConnectorManager，实现全局统一的优先级回退机制。

优先级:
  Wind MCP (100) > iFinD MCP (80) > AKShare (50) > Sina (30) > 本地缓存 (10)
"""
from __future__ import annotations

import os
import sys
import time
import logging
from typing import Dict, List, Optional, Any

from quant_modules.data_layer import DataConnector, DataConnectorManager

logger = logging.getLogger('connectors')

# ── 确保 11_量化策略 目录在 sys.path 中 ──
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)


class WindMCPConnector(DataConnector):
    """Wind MCP 数据源连接器 — 全局优先级第1位"""
    name = "wind_mcp"
    priority = 100

    def __init__(self):
        super().__init__()
        self._api_key_set = bool(os.environ.get('WIND_API_KEY', ''))

    def connect(self) -> bool:
        """尝试连接 Wind MCP，成功返回 True"""
        if not self._api_key_set:
            logger.debug("[WindMCP] WIND_API_KEY 未设置，跳过")
            self.available = False
            return False

        try:
            from wind_mcp_fetcher import wind_check_connection
            status = wind_check_connection()
            if status.get('connected'):
                self._connected = True
                self.available = True
                logger.info("[WindMCP] 连接成功, 延迟 %.0fms, 测试价 %.3f",
                           status.get('latency_ms', -1),
                           status.get('test_price', 0))
                return True
            else:
                logger.warning("[WindMCP] 连接测试失败: API Key 有效但无数据返回")
        except ImportError:
            logger.warning("[WindMCP] wind_mcp_fetcher 模块未找到")
        except Exception as e:
            logger.warning("[WindMCP] 连接异常: %s", e)

        self.available = False
        return False

    def _get_quote_impl(self, code: str) -> Optional[Dict[str, float]]:
        try:
            from wind_mcp_fetcher import wind_get_quote
            is_fund = code.startswith(('5', '1', '16'))
            result = wind_get_quote(code, is_fund=is_fund)
            if result and result.get('price'):
                return {
                    'price': result['price'],
                    'change': result.get('change', 0),
                    'source': 'wind_mcp',
                }
        except Exception as e:
            logger.debug("[WindMCP] get_quote(%s) 失败: %s", code, e)
        return None

    def _get_quotes_batch_impl(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        try:
            from wind_mcp_fetcher import wind_get_batch_quotes
            results = {}
            # 分流: ETF/基金 vs 股票
            funds = [c for c in codes if c.startswith(('5', '1', '16'))]
            stocks = [c for c in codes if c not in funds]

            if funds:
                fund_results = wind_get_batch_quotes(funds, is_fund=True)
                for code, data in fund_results.items():
                    if data.get('price'):
                        results[code] = {
                            'price': data['price'],
                            'change': data.get('change', 0),
                            'source': 'wind_mcp',
                        }

            if stocks:
                stock_results = wind_get_batch_quotes(stocks, is_fund=False)
                for code, data in stock_results.items():
                    if data.get('price'):
                        results[code] = {
                            'price': data['price'],
                            'change': data.get('change', 0),
                            'source': 'wind_mcp',
                        }

            return results
        except Exception as e:
            logger.debug("[WindMCP] batch_quotes 失败: %s", e)
        return {}

    def _get_history_impl(self, code: str, start_date: str, end_date: str) -> Any:
        try:
            from wind_mcp_fetcher import wind_get_kline
            is_fund = code.startswith(('5', '1', '16'))
            return wind_get_kline(code, days=30, is_fund=is_fund)
        except Exception as e:
            logger.debug("[WindMCP] get_kline(%s) 失败: %s", code, e)
        return None


class IFinDMCPConnector(DataConnector):
    """iFinD MCP 数据源连接器 — 全局优先级第2位 (P1 强制回退)"""
    name = "ifind_mcp"
    priority = 80

    def __init__(self):
        super().__init__()
        self._client = None
        self._token_set = bool(os.environ.get('IFIND_TOKEN', ''))

    def connect(self) -> bool:
        if not self._token_set:
            logger.debug("[iFinD] IFIND_TOKEN 未设置，跳过")
            self.available = False
            return False

        try:
            from ifind_client import IFindClient
            self._client = IFindClient()
            # 简单测试: 获取沪深300指数
            test = self._client.get_index_latest('000300')
            if test:
                self._connected = True
                self.available = True
                logger.info("[iFinD] 连接成功, 沪深300=%.2f", test.get('price', 0))
                return True
        except ImportError:
            logger.warning("[iFinD] ifind_client 模块未找到")
        except Exception as e:
            logger.warning("[iFinD] 连接异常: %s", e)

        self.available = False
        return False

    def _get_quote_impl(self, code: str) -> Optional[Dict[str, float]]:
        if not self._client:
            return None
        try:
            if code.startswith(('5', '1', '16')):
                data = self._client.get_etf_quotes([code])
            else:
                data = self._client.get_stock_quote(code)
            if data:
                quote = data[0] if isinstance(data, list) else data
                price = quote.get('price') or quote.get('close') or quote.get('latest_price')
                if price:
                    return {
                        'price': float(price),
                        'change': float(quote.get('change', 0)),
                        'source': 'ifind_mcp',
                    }
        except Exception as e:
            logger.debug("[iFinD] get_quote(%s) 失败: %s", code, e)
        return None

    def _get_quotes_batch_impl(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        if not self._client:
            return {}
        results = {}
        try:
            funds = [c for c in codes if c.startswith(('5', '1', '16'))]
            stocks = [c for c in codes if c not in funds]

            if funds:
                fund_data = self._client.get_etf_quotes(funds)
                if fund_data:
                    for item in fund_data:
                        code = item.get('code', '')
                        if code and item.get('price'):
                            results[code] = {
                                'price': float(item['price']),
                                'change': float(item.get('change', 0)),
                                'source': 'ifind_mcp',
                            }

            for stock in stocks:
                data = self._client.get_stock_quote(stock)
                if data:
                    quote = data[0] if isinstance(data, list) else data
                    price = quote.get('price') or quote.get('close')
                    if price:
                        results[stock] = {
                            'price': float(price),
                            'change': float(quote.get('change', 0)),
                            'source': 'ifind_mcp',
                        }
        except Exception as e:
            logger.debug("[iFinD] batch_quotes 失败: %s", e)
        return results

    def _get_history_impl(self, code: str, start_date: str, end_date: str) -> Any:
        if not self._client:
            return None
        try:
            if code.startswith(('5', '1', '16')):
                return self._client.get_etf_historical(code, start_date, end_date)
            else:
                return self._client.get_stock_kline(code, start_date, end_date)
        except Exception as e:
            logger.debug("[iFinD] get_history(%s) 失败: %s", code, e)
        return None


class SinaConnector(DataConnector):
    """新浪财经 API 连接器 — 免费备用数据源"""
    name = "sina_api"
    priority = 30

    def connect(self) -> bool:
        try:
            import urllib.request
            import re
            # 测试获取一只高流动性标的
            url = "http://hq.sinajs.cn/list=sh600519"
            req = urllib.request.Request(url, headers={'Referer': 'https://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read().decode('gb2312', errors='replace')
                if data and len(data) > 30:
                    self._connected = True
                    self.available = True
                    logger.info("[Sina] API 连接成功")
                    return True
        except Exception as e:
            logger.warning("[Sina] 连接失败: %s", e)
        self.available = False
        return False

    def _get_quote_impl(self, code: str) -> Optional[Dict[str, float]]:
        try:
            import urllib.request
            import re

            if code.startswith(('6', '5')):
                sina_code = f"sh{code}"
            else:
                sina_code = f"sz{code}"

            url = f"http://hq.sinajs.cn/list={sina_code}"
            req = urllib.request.Request(url, headers={'Referer': 'https://finance.sina.com.cn'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read().decode('gb2312', errors='replace')

            if raw and '="' in raw:
                parts = raw.split('="')[1].split(',')
                if len(parts) >= 4:
                    price = float(parts[3]) if parts[3] else 0
                    prev_close = float(parts[2]) if parts[2] else 0
                    change = round((price - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0
                    if price > 0:
                        return {'price': price, 'change': change, 'source': 'sina'}
        except Exception as e:
            logger.debug("[Sina] get_quote(%s) 失败: %s", code, e)
        return None

    def _get_quotes_batch_impl(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        results = {}
        for code in codes:
            quote = self._get_quote_impl(code)
            if quote:
                results[code] = quote
        return results

    def _get_history_impl(self, code: str, start_date: str, end_date: str) -> Any:
        return None  # 新浪不提供历史K线


class LocalCacheConnector(DataConnector):
    """本地缓存连接器 — 兜底数据源"""
    name = "local_cache"
    priority = 10

    def __init__(self):
        super().__init__()
        self._cache_file = os.path.join(_BASE, 'config', 'price_cache.json')

    def connect(self) -> bool:
        self._connected = True
        self.available = True
        return True

    def _load_cache(self) -> Dict:
        try:
            if os.path.exists(self._cache_file):
                import json
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _get_quote_impl(self, code: str) -> Optional[Dict[str, float]]:
        cache = self._load_cache()
        if code in cache:
            entry = cache[code]
            if isinstance(entry, dict):
                entry['source'] = 'local_cache'
                return entry
        return None

    def _get_quotes_batch_impl(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        cache = self._load_cache()
        results = {}
        for code in codes:
            if code in cache:
                entry = cache[code]
                if isinstance(entry, dict):
                    entry['source'] = 'local_cache'
                    results[code] = entry
        return results

    def _get_history_impl(self, code: str, start_date: str, end_date: str) -> Any:
        cache = self._load_cache()
        history_key = f"history_{code}"
        return cache.get(history_key)


def register_all_connectors(connector_manager: DataConnectorManager) -> int:
    """
    注册所有可用数据源连接器到 DataConnectorManager

    按优先级从高到低依次尝试连接:
      Wind MCP (100) > iFinD MCP (80) > Sina API (30) > 本地缓存 (10)

    每个连接器 connect() 成功后才标记 available=True，
    管理器会自动选择优先级最高的可用连接器。

    Returns:
        成功注册的连接器数量
    """
    connectors = [
        WindMCPConnector(),
        IFinDMCPConnector(),
        SinaConnector(),
        LocalCacheConnector(),
    ]

    registered = 0
    for conn in connectors:
        try:
            connector_manager.register_connector(conn)
            # 尝试连接（connect() 内部设置 self.available）
            conn.connect()
            if conn.available:
                registered += 1
        except Exception as e:
            logger.warning("注册连接器 %s 失败: %s", conn.name, e)

    logger.info("已注册 %d/%d 个数据源连接器", registered, len(connectors))
    return registered
