# -*- coding: utf-8 -*-
"""
合并数据层: DataCache + DataConnector + DataConnectorManager
从主文件抽取，统一管理和缓存数据连接
"""

import time
from typing import Dict, Any, Optional, List

from bootstrap import logger, DataSourceError


class DataCache:
    """轻量级数据缓存"""

    def __init__(self, ttl_seconds: int = 300, max_size_mb: int = 100):
        self._cache = {}
        self._timestamps = {}
        self.ttl_seconds = ttl_seconds
        self.max_size_mb = max_size_mb

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            age = time.time() - self._timestamps.get(key, 0)
            if age < self.ttl_seconds:
                return self._cache[key]
            del self._cache[key]
            del self._timestamps[key]
        return None

    def set(self, key: str, value: Any):
        self._cache[key] = value
        self._timestamps[key] = time.time()

    def clear(self):
        self._cache.clear()
        self._timestamps.clear()

    def stats(self) -> dict:
        return {'entries': len(self._cache), 'ttl_seconds': self.ttl_seconds}


class DataConnector:
    """数据源连接器基类 — 支持重试和缓存"""
    name = "base"
    priority = 0
    available = False

    def __init__(self):
        self._connected = False
        self._cache = DataCache()

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self):
        self._connected = False

    def get_quote(self, code: str) -> Optional[Dict[str, float]]:
        cache_key = f"quote_{code}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        result = self._with_retry(lambda: self._get_quote_impl(code))
        if result:
            self._cache.set(cache_key, result)
        return result

    def get_quotes_batch(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        results = {}
        uncached_codes = []
        for code in codes:
            cache_key = f"quote_{code}"
            cached = self._cache.get(cache_key)
            if cached:
                results[code] = cached
            else:
                uncached_codes.append(code)
        if uncached_codes:
            batch_result = self._with_retry(lambda: self._get_quotes_batch_impl(uncached_codes))
            if batch_result:
                for code, data in batch_result.items():
                    results[code] = data
                    self._cache.set(f"quote_{code}", data)
        return results

    def get_history(self, code: str, start_date: str, end_date: str) -> Any:
        cache_key = f"history_{code}_{start_date}_{end_date}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        result = self._with_retry(lambda: self._get_history_impl(code, start_date, end_date))
        if result:
            self._cache.set(cache_key, result)
        return result

    def _get_quote_impl(self, code: str) -> Optional[Dict[str, float]]:
        raise NotImplementedError

    def _get_quotes_batch_impl(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        raise NotImplementedError

    def _get_history_impl(self, code: str, start_date: str, end_date: str) -> Any:
        raise NotImplementedError

    def _with_retry(self, func, max_retries: int = 3, delay_seconds: int = 2):
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"连接器 {self.name} 操作失败，重试 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(delay_seconds * (attempt + 1))
                else:
                    logger.error(f"连接器 {self.name} 操作失败，已达最大重试次数: {e}")
                    raise

    @property
    def connected(self) -> bool:
        return self._connected


class DataConnectorManager:
    """连接器管理器 — 支持优先级回退和自动降级"""

    def __init__(self):
        self.connectors = []
        self._active_connector = None
        self._fallback_mode = False

    def register_connector(self, connector: DataConnector):
        self.connectors.append(connector)
        self.connectors.sort(key=lambda x: x.priority, reverse=True)

    def get_active_connector(self, force_reconnect: bool = False) -> Optional[DataConnector]:
        if not force_reconnect and self._active_connector and self._active_connector.connected:
            return self._active_connector
        for connector in self.connectors:
            if connector.available:
                try:
                    if connector.connect():
                        self._active_connector = connector
                        self._fallback_mode = (connector.priority < max(c.priority for c in self.connectors))
                        logger.info(f"已激活数据源连接器: {connector.name} (优先级: {connector.priority})")
                        if self._fallback_mode:
                            logger.warning("当前使用降级模式，主数据源不可用")
                        return connector
                except Exception as e:
                    logger.warning(f"连接器 {connector.name} 连接失败: {e}")
        return None

    def get_quote(self, code: str) -> Optional[Dict[str, float]]:
        connector = self.get_active_connector()
        if connector:
            try:
                return connector.get_quote(code)
            except Exception as e:
                logger.warning(f"连接器 {connector.name} 获取行情失败: {e}")
                self._active_connector = None
                return self.get_quote(code)
        return None

    def get_quotes_batch(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        connector = self.get_active_connector()
        if connector:
            try:
                return connector.get_quotes_batch(codes)
            except Exception as e:
                logger.warning(f"连接器 {connector.name} 批量获取失败: {e}")
                self._active_connector = None
                return self.get_quotes_batch(codes)
        return {}

    def list_connectors(self) -> List[Dict[str, Any]]:
        return [{'name': c.name, 'priority': c.priority, 'available': c.available, 'connected': c.connected}
                for c in self.connectors]

    def get_status(self) -> dict:
        return {
            'active_connector': self._active_connector.name if self._active_connector else None,
            'fallback_mode': self._fallback_mode,
            'total_connectors': len(self.connectors),
            'available_connectors': sum(1 for c in self.connectors if c.available)
        }
