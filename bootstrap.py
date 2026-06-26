# -*- coding: utf-8 -*-
"""
量化策略系统 v5.1 — 公共引导模块
抽取自主文件，统一管理导入、路径、日志、事件追踪和工具类
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, time as dt_time
from typing import Dict, Any, Optional, List

# Windows控制台UTF-8编码支持
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# 日志配置
from utils.logging_manager import setup_logging, get_logger

setup_logging()
logger = get_logger('quant')

LOG_DIR = os.path.join(BASE_DIR, 'logs')

# 事件追踪
from utils.event_tracker import EventTracker, track_event, get_event_tracker

event_tracker = get_event_tracker()


class PerformanceTracker:
    """性能追踪器 - 兼容旧代码，内部使用 EventTracker"""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.start_time = time.time()
        self._subtasks = []
        self._session_id = f"task_{task_name}_{int(time.time())}"
        event_tracker.start_session(self._session_id, meta={'task': task_name})

    def record_subtask(self, name: str, duration_ms: float):
        self._subtasks.append({'name': name, 'duration_ms': duration_ms})

    def finish(self) -> dict:
        total_ms = (time.time() - self.start_time) * 1000
        logger.info(f"任务完成: {self.task_name} | 总耗时: {total_ms:.2f}ms",
                   extra={'operation': self.task_name, 'duration_ms': total_ms})
        if self._subtasks:
            for subtask in self._subtasks:
                logger.info(f"  └─ {subtask['name']}: {subtask['duration_ms']:.2f}ms",
                           extra={'operation': self.task_name, 'duration_ms': subtask['duration_ms']})
        event_tracker.finish_session(self._session_id)
        return {'task': self.task_name, 'total_ms': total_ms, 'subtasks': self._subtasks}


class StrategyRegistry:
    """策略注册表 - 中心化策略管理与版本控制"""

    def __init__(self):
        self.strategies = {}
        self.hypotheses = {}
        self._load_strategies()

    def _load_strategies(self):
        self.strategies = {
            'mean_reversion': {
                'name': '均值回归策略',
                'description': '基于Z-score的均值回归策略，当价格偏离历史均值超过阈值时触发交易',
                'parameters': {'z_score_threshold': 2.0, 'reversion_target': 'mean', 'lookback_days': 60},
                'risk_level': 'medium', 'version': '1.0.0'
            },
            'momentum': {
                'name': '动量策略',
                'description': '追踪价格趋势，买入强势标的，卖出弱势标的',
                'parameters': {'lookback_days': 20, 'strength_threshold': 0.05},
                'risk_level': 'high', 'version': '1.0.0'
            },
            'sector_rotation': {
                'name': '行业轮动策略',
                'description': '基于行业景气度进行板块轮动配置',
                'parameters': {'rotation_frequency': 'weekly', 'top_sectors': 3},
                'risk_level': 'low', 'version': '1.0.0'
            },
            'arbitrage': {
                'name': '大宗商品套利策略',
                'description': '跨期/跨品种/跨市场套利策略',
                'parameters': {'z_score_threshold': 2.0, 'volatility_scaling': True},
                'risk_level': 'medium', 'version': '1.0.0'
            },
            'event_driven': {
                'name': '事件驱动策略',
                'description': '基于新闻事件和公告进行交易决策',
                'parameters': {'sentiment_threshold': 0.7, 'hold_days': 5},
                'risk_level': 'high', 'version': '1.0.0'
            }
        }

    def register(self, strategy_id: str, config: Dict[str, Any]):
        self.strategies[strategy_id] = config
        logger.info(f"策略已注册: {strategy_id}")

    def get(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        return self.strategies.get(strategy_id)

    def list(self) -> List[str]:
        return list(self.strategies.keys())

    def register_hypothesis(self, hypothesis_id: str, hypothesis: Dict[str, Any]):
        self.hypotheses[hypothesis_id] = {
            **hypothesis,
            'created_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        logger.info(f"研究假设已注册: {hypothesis_id}")

    def update_hypothesis(self, hypothesis_id: str, updates: Dict[str, Any]):
        if hypothesis_id in self.hypotheses:
            self.hypotheses[hypothesis_id].update(updates)


class QuantSystemError(Exception):
    """量化系统基础异常"""
    def __init__(self, message: str, code: str = 'UNKNOWN_ERROR', details: dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()


class DataSourceError(QuantSystemError):
    def __init__(self, message: str, source: str = None, details: dict = None):
        super().__init__(message, code='DATA_SOURCE_ERROR', details=details)
        self.source = source


class ConfigError(QuantSystemError):
    def __init__(self, message: str, config_path: str = None, details: dict = None):
        super().__init__(message, code='CONFIG_ERROR', details=details)
        self.config_path = config_path


class TradingError(QuantSystemError):
    def __init__(self, message: str, order_id: str = None, details: dict = None):
        super().__init__(message, code='TRADING_ERROR', details=details)
        self.order_id = order_id


class ValidationError(QuantSystemError):
    def __init__(self, message: str, field: str = None, details: dict = None):
        super().__init__(message, code='VALIDATION_ERROR', details=details)
        self.field = field


class GracefulFallback:
    """优雅降级管理器"""

    def __init__(self):
        self._fallback_handlers = {}
        self._fallback_mode = False

    def register_fallback(self, exception_type: type, handler):
        self._fallback_handlers[exception_type] = handler

    def execute_with_fallback(self, func, fallback_value=None, fallback_desc="未知操作"):
        try:
            return func()
        except Exception as e:
            for exc_type in type(e).__mro__:
                if exc_type in self._fallback_handlers:
                    handler = self._fallback_handlers[exc_type]
                    result = handler(e)
                    logger.warning(f"降级处理触发: {fallback_desc} | 异常: {type(e).__name__} | 消息: {e}")
                    self._fallback_mode = True
                    return result
            logger.warning(f"默认降级处理: {fallback_desc} | 异常: {type(e).__name__} | 消息: {e}")
            self._fallback_mode = True
            return fallback_value

    def is_fallback_mode(self) -> bool:
        return self._fallback_mode

    def reset(self):
        self._fallback_mode = False


graceful_fallback = GracefulFallback()
graceful_fallback.register_fallback(DataSourceError, lambda e: {})
graceful_fallback.register_fallback(ConfigError, lambda e: {})


def handle_exception(func):
    """全局异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except QuantSystemError as e:
            logger.error(f"量化系统异常: {e.code} | {e}",
                        extra={'error_code': e.code, 'error_details': e.details})
            raise
        except Exception as e:
            logger.error(f"未预期异常: {type(e).__name__} | {e}",
                        extra={'error_type': type(e).__name__, 'error_message': str(e)})
            raise QuantSystemError(f"系统异常: {e}", code='UNEXPECTED_ERROR')
    return wrapper


class ModuleLoader:
    """模块加载器，支持优雅降级"""

    def __init__(self):
        self._modules = {}

    def load(self, module_name, import_dict):
        try:
            module = __import__(module_name, fromlist=list(import_dict.keys()))
            self._modules[module_name] = module
            result = {}
            for attr, alias in import_dict.items():
                result[alias] = getattr(module, attr, None)
            return result
        except ImportError as e:
            logger.warning(f"模块 {module_name} 加载失败: {e}")
            return {alias: None for alias in import_dict.values()}


class ConfigManager:
    """统一配置管理器"""

    def __init__(self):
        self._configs = {}
        self._defaults = {
            'rebalance': {'threshold': 0.05, 'min_interval_days': 30, 'max_single_trade_ratio': 0.15},
            'risk': {'stop_loss_pct': 0.15, 'take_profit_pct': 0.30, 'high_risk_threshold': 0.32, 'medium_risk_threshold': 0.26},
            'etf_monitor': {'signal_high_threshold': 50_000_000_000, 'signal_medium_threshold': 10_000_000_000, 'signal_low_threshold': 2_000_000_000, 'analysis_days': 5},
            'cache': {'enabled': True, 'ttl_seconds': 300, 'max_size_mb': 100},
            'data': {'timeout_seconds': 30, 'max_retries': 3, 'retry_delay_seconds': 2},
            'trading': {'min_order_size': 100, 'price_decimal_places': 2, 'commission_rate': 0.0003},
        }

    def get(self, section: str, key: str = None, default=None):
        cfg = self._configs.get(section, self._defaults.get(section, {}))
        if key is None:
            return cfg
        return cfg.get(key, default)

    def set(self, section: str, key: str, value):
        if section not in self._configs:
            self._configs[section] = {}
        self._configs[section][key] = value


class ProgressIndicator:
    """进度指示器"""

    def __init__(self, task_name: str, total_steps: int):
        self.task_name = task_name
        self.total_steps = total_steps
        self.current = 0
        self.start_time = time.time()
        print(f"\n🔄 {task_name} [{'·' * total_steps}] 0/{total_steps}")

    def update(self, step: int, message: str = ""):
        self.current = step
        bar = '█' * step + '·' * (self.total_steps - step)
        msg = f"  {message}" if message else ""
        print(f"\r🔄 {self.task_name} [{bar}] {step}/{self.total_steps}{msg}", end='', flush=True)

    def complete(self, message: str = ""):
        elapsed = (time.time() - self.start_time)
        bar = '█' * self.total_steps
        msg = f"  {message}" if message else ""
        print(f"\r✅ {self.task_name} [{bar}] {self.total_steps}/{self.total_steps} 完成 ({elapsed:.1f}s){msg}")


def load_portfolio_config():
    """加载投资组合配置"""
    yaml_path = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
    try:
        import yaml
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.warning(f"加载portfolio.yaml失败: {e}")
        return {'assets': []}


# 全局变量 — 延迟初始化
_connector_manager = None
_strategy_registry = None


def get_connector_manager():
    """获取全局连接器管理器（延迟初始化）"""
    global _connector_manager
    if _connector_manager is None:
        from quant_modules.data_layer import DataConnectorManager
        _connector_manager = DataConnectorManager()
    return _connector_manager


def get_strategy_registry():
    """获取全局策略注册表（延迟初始化）"""
    global _strategy_registry
    if _strategy_registry is None:
        _strategy_registry = StrategyRegistry()
    return _strategy_registry
