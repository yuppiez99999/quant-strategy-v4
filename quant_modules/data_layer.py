# -*- coding: utf-8 -*-
"""数据层模块 — 缓存管理、数据源连接器与连接器管理

包含:
- DataCache: 数据缓存管理器，支持TTL和内存限制
- DataConnector: 数据源连接器基类，支持重试和缓存
- DataConnectorManager: 连接器管理器，支持优先级回退和自动降级
"""
from __future__ import annotations

import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    from utils.logging_manager import get_logger
    logger = get_logger('data_layer')
except ImportError:
    import logging
    logger = logging.getLogger('data_layer')


class DataCache:
    """数据缓存管理器 - 支持TTL和内存限制"""

    def __init__(self, ttl_seconds: int = 300, max_size_mb: int = 100):
        self._cache = {}
        self._ttl = ttl_seconds
        self._max_size_mb = max_size_mb
        self._current_size_bytes = 0

    def get(self, key: str):
        """获取缓存值"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return data
            else:
                # 过期，删除
                self._current_size_bytes -= self._estimate_size(data)
                del self._cache[key]
        return None

    def set(self, key: str, value):
        """设置缓存值"""
        # 检查内存限制
        value_size = self._estimate_size(value)
        while self._current_size_bytes + value_size > self._max_size_mb * 1024 * 1024:
            # 删除最旧的缓存
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            oldest_size = self._estimate_size(self._cache[oldest_key][0])
            self._current_size_bytes -= oldest_size
            del self._cache[oldest_key]

        self._cache[key] = (value, time.time())
        self._current_size_bytes += value_size

    def _estimate_size(self, obj) -> int:
        """估算对象大小（字节）"""
        return sys.getsizeof(obj)

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._current_size_bytes = 0

    def stats(self) -> dict:
        """获取缓存统计"""
        return {
            'items': len(self._cache),
            'size_mb': self._current_size_bytes / (1024 * 1024),
            'ttl_seconds': self._ttl
        }


class DataConnector:
    """数据源连接器基类 - 支持重试和缓存"""
    name = "base"
    priority = 0
    available = False

    def __init__(self):
        self._connected = False
        self._cache = DataCache()
        self._retry_count = 0

    def connect(self) -> bool:
        """建立连接"""
        self._connected = True
        return True

    def disconnect(self):
        """断开连接"""
        self._connected = False

    def get_quote(self, code: str) -> Optional[Dict[str, float]]:
        """获取单个标的行情（带缓存和重试）"""
        # 先尝试缓存
        cache_key = f"quote_{code}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        # 带重试的获取
        result = self._with_retry(lambda: self._get_quote_impl(code))

        if result:
            self._cache.set(cache_key, result)

        return result

    def get_quotes_batch(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        """批量获取行情（带缓存）"""
        results = {}
        uncached_codes = []

        # 先检查缓存
        for code in codes:
            cache_key = f"quote_{code}"
            cached = self._cache.get(cache_key)
            if cached:
                results[code] = cached
            else:
                uncached_codes.append(code)

        # 批量获取未缓存的
        if uncached_codes:
            batch_result = self._with_retry(lambda: self._get_quotes_batch_impl(uncached_codes))
            if batch_result:
                for code, data in batch_result.items():
                    results[code] = data
                    self._cache.set(f"quote_{code}", data)

        return results

    def get_history(self, code: str, start_date: str, end_date: str) -> Any:
        """获取历史数据"""
        cache_key = f"history_{code}_{start_date}_{end_date}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        result = self._with_retry(lambda: self._get_history_impl(code, start_date, end_date))

        if result:
            self._cache.set(cache_key, result)

        return result

    def _get_quote_impl(self, code: str) -> Optional[Dict[str, float]]:
        """子类实现：获取单个行情"""
        raise NotImplementedError

    def _get_quotes_batch_impl(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        """子类实现：批量获取行情"""
        raise NotImplementedError

    def _get_history_impl(self, code: str, start_date: str, end_date: str) -> Any:
        """子类实现：获取历史数据"""
        raise NotImplementedError

    def _with_retry(self, func, max_retries: int = 3, delay_seconds: int = 2):
        """带重试的执行包装"""
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
    """连接器管理器 - 支持优先级回退和自动降级

    v5.7 Phase 1 增强:
    - 降级历史追踪 (_fallback_history)
    - 主动健康探测 (check_health)
    - 数据源层级标识 (data_source_label)
    """

    def __init__(self):
        self.connectors = []
        self._active_connector = None
        self._fallback_mode = False
        # v5.7 新增：降级事件追踪
        self._fallback_history: List[Dict[str, Any]] = []
        self._max_priority = 0  # 最高可用优先级
        self._health_check_interval = 120  # 健康探测间隔（秒）
        self._last_health_check = 0

    def register_connector(self, connector: DataConnector):
        """注册连接器"""
        self.connectors.append(connector)
        self.connectors.sort(key=lambda x: x.priority, reverse=True)
        self._max_priority = max(c.priority for c in self.connectors) if self.connectors else 0

    def get_active_connector(self, force_reconnect: bool = False) -> Optional[DataConnector]:
        """获取当前活跃连接器"""
        if not force_reconnect and self._active_connector and self._active_connector.connected:
            return self._active_connector

        for connector in self.connectors:
            if connector.available:
                try:
                    if connector.connect():
                        prev_connector = self._active_connector
                        self._active_connector = connector
                        is_fallback = (connector.priority < self._max_priority)
                        self._fallback_mode = is_fallback
                        logger.info(f"已激活数据源连接器: {connector.name} (优先级: {connector.priority})")

                        # v5.7 新增：记录降级事件
                        if prev_connector and connector is not prev_connector:
                            self._record_fallback_event(prev_connector.name, connector.name)

                        if self._fallback_mode:
                            logger.warning(f"当前使用降级模式，主数据源不可用")
                        return connector
                except Exception as e:
                    logger.warning(f"连接器 {connector.name} 连接失败: {e}")

        return None

    def get_quote(self, code: str) -> Optional[Dict[str, float]]:
        """获取行情（自动降级）"""
        connector = self.get_active_connector()
        if connector:
            try:
                return connector.get_quote(code)
            except Exception as e:
                logger.warning(f"连接器 {connector.name} 获取行情失败: {e}")
                self._record_fallback_event(connector.name, None)
                self._active_connector = None
                return self.get_quote(code)  # 尝试下一个连接器

        return None

    def get_quotes_batch(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        """批量获取行情"""
        connector = self.get_active_connector()
        if connector:
            try:
                return connector.get_quotes_batch(codes)
            except Exception as e:
                logger.warning(f"连接器 {connector.name} 批量获取失败: {e}")
                self._record_fallback_event(connector.name, None)
                self._active_connector = None
                return self.get_quotes_batch(codes)  # 尝试下一个连接器

        return {}

    # ── v5.7 Phase 1 新增 ──

    def _record_fallback_event(self, from_connector: str, to_connector: str = None):
        """记录降级事件"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'from': from_connector,
            'to': to_connector or 'unknown',
            'date': (datetime.now()).strftime('%Y-%m-%d'),
        }
        self._fallback_history.append(event)
        # 保留最近100条
        if len(self._fallback_history) > 100:
            self._fallback_history = self._fallback_history[-100:]

    def check_health(self) -> Dict[str, Any]:
        """主动健康探测 - 检查所有连接器状态"""
        now = time.time()
        if now - self._last_health_check < self._health_check_interval:
            return {
                'status': 'cached',
                'last_check_ago': int(now - self._last_health_check),
                'active': self._active_connector.name if self._active_connector else None,
            }

        self._last_health_check = now
        results = {}
        for connector in self.connectors:
            try:
                alive = connector.available and connector.connect()
                results[connector.name] = {
                    'alive': alive,
                    'priority': connector.priority,
                    'connected': connector.connected,
                }
            except Exception:
                results[connector.name] = {
                    'alive': False,
                    'priority': connector.priority,
                    'connected': False,
                }

        return {
            'status': 'checked',
            'timestamp': datetime.now().isoformat(),
            'active': self._active_connector.name if self._active_connector else None,
            'connectors': results,
        }

    def get_data_source_label(self) -> str:
        """获取当前数据源的层级标签（用于报告展示）

        Returns:
            'Wind (P0)' / 'iFinD (P1)' / 'AKShare (P2)' / '新浪 (P3)' / '本地缓存 (P4)' / 'None'
        """
        if self._active_connector:
            labels = {
                'Wind': '🟢 Wind (P0)',
                'wind': '🟢 Wind (P0)',
                'iFinD': '🟡 iFinD (P1)',
                'ifind': '🟡 iFinD (P1)',
                'AKShare': '🟠 AKShare (P2)',
                'akshare': '🟠 AKShare (P2)',
                'Sina': '🔴 新浪 (P3, 已降级)',
                'sina': '🔴 新浪 (P3, 已降级)',
                'LocalCache': '⚠️ 本地缓存 (P4, 已降级)',
                'local_cache': '⚠️ 本地缓存 (P4, 已降级)',
            }
            return labels.get(self._active_connector.name,
                            f"❓ {self._active_connector.name}")
        return '❌ 无数据源'

    def get_fallbacks_today(self) -> int:
        """获取今日降级次数"""
        today = datetime.now().strftime('%Y-%m-%d')
        return sum(1 for f in self._fallback_history if f['date'] == today)

    def get_recent_fallbacks(self, n: int = 5) -> List[Dict]:
        """获取最近N次降级记录"""
        return self._fallback_history[-n:]

    def list_connectors(self) -> List[Dict[str, Any]]:
        """列出所有连接器"""
        return [
            {
                'name': c.name,
                'priority': c.priority,
                'available': c.available,
                'connected': c.connected
            }
            for c in self.connectors
        ]

    def get_status(self) -> dict:
        """获取连接器状态摘要（v5.7 增强版）"""
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            'active_connector': self._active_connector.name if self._active_connector else None,
            'active_priority': self._active_connector.priority if self._active_connector else 0,
            'data_source_label': self.get_data_source_label(),
            'fallback_mode': self._fallback_mode,
            'total_connectors': len(self.connectors),
            'available_connectors': sum(1 for c in self.connectors if c.available),
            # v5.7 新增
            'total_fallbacks_today': self.get_fallbacks_today(),
            'recent_fallbacks': self.get_recent_fallbacks(5),
            'health_check': self.check_health(),
        }
