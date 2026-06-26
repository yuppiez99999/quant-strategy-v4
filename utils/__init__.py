# -*- coding: utf-8 -*-
"""
量化策略系统 v5.0 - 工具模块
借鉴 TradingAgents-CN 架构模式重构
"""

from .logging_manager import (
    get_logger,
    get_logger_manager,
    setup_logging,
    QuantSystemLogger,
)
from .event_tracker import (
    EventTracker,
    track_event,
    track_operation,
    get_event_tracker,
)
from .data_source_manager import (
    DataSourceRegistry,
    PriorityDataSourceManager,
    CacheStats,
    get_data_source_manager,
)
from .console_encoding import setup_utf8_console
from .env_loader import load_dotenv
from .report_archiver import get_archive_dir, archive_report

__all__ = [
    # 日志
    'get_logger', 'get_logger_manager', 'setup_logging', 'QuantSystemLogger',
    # 事件追踪
    'EventTracker', 'track_event', 'track_operation', 'get_event_tracker',
    # 数据源
    'DataSourceRegistry', 'PriorityDataSourceManager', 'CacheStats',
    'get_data_source_manager',
    # 通用工具
    'setup_utf8_console', 'load_dotenv', 'get_archive_dir', 'archive_report',
]