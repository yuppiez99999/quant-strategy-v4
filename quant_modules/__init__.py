# -*- coding: utf-8 -*-
"""quant_modules - 量化策略系统 v5.2 模块化拆分

模块结构:
  - wind_mcp: Wind MCP 数据获取工具函数
  - core: 核心基础类（性能追踪、策略注册表、异常处理、配置管理）
  - data_layer: 数据缓存与连接器
  - rebalance: Excel驱动再平衡引擎
  - portfolio: 投资组合优化引擎
  - monitors: 监控模块（康波、ETF、K线扫描）
  - dynamic_position: 动态仓位管理（v5.2新增）
"""

from quant_modules.wind_mcp import (
    _wind_code,
    _wind_mcp_call,
    _wind_mcp_fetch_kline,
    _wind_mcp_fetch_quote,
    PORTFOLIO_TARGETS,
    WIND_MCP_SKILL_DIR,
)

from quant_modules.core import (
    PerformanceTracker,
    StrategyRegistry,
    QuantSystemError,
    DataSourceError,
    ConfigError,
    TradingError,
    ValidationError,
    GracefulFallback,
    handle_exception,
    ModuleLoader,
    ConfigManager,
    load_portfolio_config,
    _classify_asset_type,
    compute_trade_cost,
    ProgressIndicator,
)

from quant_modules.data_layer import (
    DataCache,
    DataConnector,
    DataConnectorManager,
)

from quant_modules.dynamic_position import DynamicPositionManager

__all__ = [
    # wind_mcp
    '_wind_code', '_wind_mcp_call', '_wind_mcp_fetch_kline', '_wind_mcp_fetch_quote',
    'PORTFOLIO_TARGETS', 'WIND_MCP_SKILL_DIR',
    # core
    'PerformanceTracker', 'StrategyRegistry',
    'QuantSystemError', 'DataSourceError', 'ConfigError', 'TradingError', 'ValidationError',
    'GracefulFallback', 'handle_exception', 'ModuleLoader', 'ConfigManager',
    'load_portfolio_config', '_classify_asset_type', 'compute_trade_cost', 'ProgressIndicator',
    # data_layer
    'DataCache', 'DataConnector', 'DataConnectorManager',
    # dynamic_position
    'DynamicPositionManager',
]
