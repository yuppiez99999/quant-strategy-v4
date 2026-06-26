# -*- coding: utf-8 -*-
"""核心基础模块 — 性能追踪、策略注册表、异常处理、配置管理、交易成本

包含:
- PerformanceTracker: 性能追踪器（委托 EventTracker）
- StrategyRegistry: 策略注册表
- 异常类族: QuantSystemError, DataSourceError, ConfigError, TradingError, ValidationError
- GracefulFallback: 优雅降级管理器
- handle_exception: 全局异常处理装饰器
- ModuleLoader: 模块加载器
- ConfigManager: 统一配置管理器
- load_portfolio_config: 加载组合配置
- _classify_asset_type: 资产类型分类
- compute_trade_cost: 精细化交易成本计算
- ProgressIndicator: 进度指示器
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from utils.logging_manager import get_logger
    logger = get_logger('quant_core')
except ImportError:
    import logging
    logger = logging.getLogger('quant_core')

try:
    from utils.event_tracker import EventTracker, track_event, get_event_tracker
    event_tracker = get_event_tracker()
except ImportError:
    event_tracker = None


class PerformanceTracker:
    """性能追踪器 - 兼容旧代码，内部使用 EventTracker"""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.start_time = time.time()
        self._subtasks = []
        self._session_id = f"task_{task_name}_{int(time.time())}"
        if event_tracker:
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
        if event_tracker:
            event_tracker.finish_session(self._session_id)
        return {
            'task': self.task_name,
            'total_ms': total_ms,
            'subtasks': self._subtasks
        }


class StrategyRegistry:
    """策略注册表 - 中心化策略管理与版本控制"""

    def __init__(self):
        self.strategies = {}
        self.hypotheses = {}
        self._load_strategies()

    def _load_strategies(self):
        """加载内置策略定义"""
        self.strategies = {
            'mean_reversion': {
                'name': '均值回归策略',
                'description': '基于Z-score的均值回归策略，当价格偏离历史均值超过阈值时触发交易',
                'parameters': {'z_score_threshold': 2.0, 'reversion_target': 'mean', 'lookback_days': 60},
                'risk_level': 'medium',
                'version': '1.0.0'
            },
            'momentum': {
                'name': '动量策略',
                'description': '追踪价格趋势，买入强势标的，卖出弱势标的',
                'parameters': {'lookback_days': 20, 'strength_threshold': 0.05},
                'risk_level': 'high',
                'version': '1.0.0'
            },
            'sector_rotation': {
                'name': '行业轮动策略',
                'description': '基于行业景气度进行板块轮动配置',
                'parameters': {'rotation_frequency': 'weekly', 'top_sectors': 3},
                'risk_level': 'low',
                'version': '1.0.0'
            },
            'arbitrage': {
                'name': '大宗商品套利策略',
                'description': '跨期/跨品种/跨市场套利策略',
                'parameters': {'z_score_threshold': 2.0, 'volatility_scaling': True},
                'risk_level': 'medium',
                'version': '1.0.0'
            },
            'event_driven': {
                'name': '事件驱动策略',
                'description': '基于新闻事件和公告进行交易决策',
                'parameters': {'sentiment_threshold': 0.7, 'hold_days': 5},
                'risk_level': 'high',
                'version': '1.0.0'
            },
            # ── 四大投资大师理论策略 (v5.4 新增) ──
            'soros_reflexivity': {
                'name': '索罗斯反身性策略',
                'description': '识别市场偏见与价格的正反馈循环，检测盛衰周期阶段，衡量远离均衡程度',
                'parameters': {'reflexivity_threshold': 0.6, 'zscore_extreme': 2.0, 'volume_spike_multiple': 1.5},
                'risk_level': 'medium',
                'version': '1.0.0'
            },
            'dalio_economic_machine': {
                'name': '达利奥经济机器策略',
                'description': '基于债务周期与经济环境四象限的宏观配置策略，风险平价与全天候配置',
                'parameters': {'debt_warning_threshold': 0.6, 'regime_mapping': 'growth_inflation_matrix'},
                'risk_level': 'low',
                'version': '1.0.0'
            },
            'first_principles': {
                'name': '第一性原理策略',
                'description': '将企业价值分解到最基本驱动因素，从底层推演内在价值，挑战市场共识叙事',
                'parameters': {'discount_rate': 0.10, 'terminal_growth': 0.03, 'forecast_years': 5},
                'risk_level': 'medium',
                'version': '1.0.0'
            },
            'buffett_munger': {
                'name': '巴菲特芒格价值策略',
                'description': '护城河评估+安全边际计算+能力圈分析+企业质量评分，长期价值投资框架',
                'parameters': {'moat_passing_score': 50, 'margin_safety_target': 0.15},
                'risk_level': 'low',
                'version': '1.0.0'
            },
            'theory_fusion': {
                'name': '四大理论融合策略',
                'description': '加权融合四大投资理论决策，一致性检验与冲突检测，生成综合信号',
                'parameters': {
                    'weights': {'索罗斯反身性': 0.20, '达利奥经济机器': 0.25, '第一性原理': 0.25, '巴菲特芒格模型': 0.30},
                    'agreement_threshold': 0.6
                },
                'risk_level': 'low',
                'version': '1.0.0'
            },
            # ── 衍生品策略 (v5.5 新增) ──
            'futures_calendar_spread': {
                'name': '期货跨期套利策略',
                'description': '利用期货期限结构Contango/Backwardation进行跨期套利，近月-远月价差回归',
                'parameters': {'z_score_threshold': 2.0, 'max_contracts': 3, 'month_spread_min': 2},
                'risk_level': 'medium',
                'version': '1.0.0'
            },
            'options_volatility': {
                'name': '期权波动率策略',
                'description': '基于隐含波动率偏斜和PCR的期权策略，IV Rank驱动的跨式/宽跨式组合',
                'parameters': {'iv_rank_threshold': 70, 'pcr_extreme': 1.2, 'skew_threshold': 0.05},
                'risk_level': 'high',
                'version': '1.0.0'
            },
            'commodity_arbitrage': {
                'name': '商品跨品种套利策略',
                'description': '基于产业链上下游利润的跨品种套利(钢厂利润/压榨利润/聚酯链)，Wind MCP数据驱动',
                'parameters': {'z_score_entry': 2.0, 'z_score_exit': 0.5, 'max_holding_days': 20},
                'risk_level': 'medium',
                'version': '1.0.0'
            }
        }

    def register(self, strategy_id: str, config: Dict[str, Any]):
        """注册新策略"""
        self.strategies[strategy_id] = config
        logger.info(f"策略已注册: {strategy_id}")

    def get(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取策略配置"""
        return self.strategies.get(strategy_id)

    def list(self) -> List[str]:
        """列出所有策略"""
        return list(self.strategies.keys())

    def register_hypothesis(self, hypothesis_id: str, hypothesis: Dict[str, Any]):
        """注册研究假设"""
        self.hypotheses[hypothesis_id] = {
            **hypothesis,
            'created_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        logger.info(f"研究假设已注册: {hypothesis_id}")

    def update_hypothesis(self, hypothesis_id: str, updates: Dict[str, Any]):
        """更新假设状态"""
        if hypothesis_id in self.hypotheses:
            self.hypotheses[hypothesis_id].update(updates)
            logger.info(f"研究假设已更新: {hypothesis_id}")

    def list_hypotheses(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出研究假设"""
        if status:
            return [h for h in self.hypotheses.values() if h.get('status') == status]
        return list(self.hypotheses.values())


# ============================================================
# 统一异常处理 - 自定义异常类和优雅降级机制
# ============================================================

class QuantSystemError(Exception):
    """量化系统基础异常"""
    def __init__(self, message: str, code: str = 'UNKNOWN_ERROR', details: dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

class DataSourceError(QuantSystemError):
    """数据源异常"""
    def __init__(self, message: str, source: str = None, details: dict = None):
        super().__init__(message, code='DATA_SOURCE_ERROR', details=details)
        self.source = source

class ConfigError(QuantSystemError):
    """配置异常"""
    def __init__(self, message: str, config_path: str = None, details: dict = None):
        super().__init__(message, code='CONFIG_ERROR', details=details)
        self.config_path = config_path

class TradingError(QuantSystemError):
    """交易异常"""
    def __init__(self, message: str, order_id: str = None, details: dict = None):
        super().__init__(message, code='TRADING_ERROR', details=details)
        self.order_id = order_id

class ValidationError(QuantSystemError):
    """验证异常"""
    def __init__(self, message: str, field: str = None, details: dict = None):
        super().__init__(message, code='VALIDATION_ERROR', details=details)
        self.field = field


class GracefulFallback:
    """优雅降级管理器 - 管理异常情况下的降级策略"""

    def __init__(self):
        self._fallback_handlers = {}
        self._fallback_mode = False

    def register_fallback(self, exception_type: type, handler):
        """注册降级处理器"""
        self._fallback_handlers[exception_type] = handler

    def execute_with_fallback(self, func, fallback_value=None, fallback_desc="未知操作"):
        """执行函数并在异常时降级"""
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
        """是否处于降级模式"""
        return self._fallback_mode

    def reset(self):
        """重置降级状态"""
        self._fallback_mode = False


# 全局降级管理器
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
        """尝试加载模块，失败时记录但不抛出异常"""
        try:
            module = __import__(module_name, fromlist=import_dict.keys())
            self._modules[module_name] = module
            result = {}
            for attr, alias in import_dict.items():
                result[alias] = getattr(module, attr, None)
            return result
        except ImportError as e:
            logger.warning(f"模块 {module_name} 加载失败: {e}")
            return {alias: None for alias in import_dict.values()}
        except Exception as e:
            logger.warning(f"模块 {module_name} 初始化失败: {e}")
            return {alias: None for alias in import_dict.values()}


class ConfigManager:
    """统一配置管理器 - 支持多格式配置文件和动态重载"""

    def __init__(self):
        self._configs = {}
        self._defaults = {
            'rebalance': {
                'threshold': 0.05,
                'min_interval_days': 30,
                'max_single_trade_ratio': 0.15,
            },
            'risk': {
                'stop_loss_pct': 0.15,
                'take_profit_pct': 0.30,
                'high_risk_threshold': 0.32,
                'medium_risk_threshold': 0.26,
            },
            'etf_monitor': {
                'signal_high_threshold': 50_000_000_000,
                'signal_medium_threshold': 10_000_000_000,
                'signal_low_threshold': 2_000_000_000,
                'analysis_days': 5,
            },
            'cache': {
                'enabled': True,
                'ttl_seconds': 300,
                'max_size_mb': 100,
            },
            'data': {
                'timeout_seconds': 30,
                'max_retries': 3,
                'retry_delay_seconds': 2,
            },
            'trading': {
                'min_order_size': 100,
                'price_decimal_places': 2,
                'commission': {
                    'stock': {'buy_rate': 0.00025, 'sell_rate': 0.00075, 'min_fee': 5.0},
                    'etf': {'buy_rate': 0.0001, 'sell_rate': 0.0001, 'min_fee': 0},
                    'bond': {'buy_rate': 0.00005, 'sell_rate': 0.00005, 'min_fee': 0},
                },
                'slippage': {
                    'low_price': 0.01,
                    'mid_price': 0.02,
                    'high_price': 0.05,
                },
            },
        }

    def load_config(self, config_type: str):
        """加载指定类型的配置"""
        if config_type in self._configs:
            return self._configs[config_type]

        config_path = os.path.join(BASE_DIR, 'config', f'{config_type}.yaml')
        if os.path.exists(config_path):
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f) or {}
                    merged = self._deep_merge(self._defaults.get(config_type, {}), file_config)
                    self._configs[config_type] = merged
                    return merged
            except Exception as e:
                logger.warning(f"加载配置文件 {config_type}.yaml 失败: {e}")

        return self._defaults.get(config_type, {})

    def get(self, config_type: str, key: str, default=None):
        """获取配置值"""
        config = self.load_config(config_type)
        return config.get(key, default)

    def _deep_merge(self, defaults: dict, overrides: dict) -> dict:
        """深度合并配置"""
        result = defaults.copy()
        for key, value in overrides.items():
            if isinstance(value, dict) and key in defaults and isinstance(defaults[key], dict):
                result[key] = self._deep_merge(defaults[key], value)
            else:
                result[key] = value
        return result

    def reload(self):
        """重新加载所有配置"""
        self._configs.clear()

    def get_all(self) -> dict:
        """获取所有配置"""
        return {k: self.load_config(k) for k in self._defaults.keys()}


# 全局配置管理器实例
config_manager = ConfigManager()


def load_portfolio_config():
    """加载组合配置（兼容旧代码）"""
    return config_manager.load_config('portfolio')


def _classify_asset_type(code: str, asset_type_hint: str = None) -> str:
    """根据代码或资产类型标注判断交易品种类别"""
    if asset_type_hint:
        h = asset_type_hint.lower()
        if 'etf' in h or '基金' in h:
            return 'etf'
        if 'bond' in h or '债券' in h:
            return 'bond'
    if code.startswith(('51', '58', '56', '159', '16', '15', '18')):
        return 'etf'
    return 'stock'


def compute_trade_cost(shares: int, price: float, side: str = 'buy', code: str = '') -> float:
    """计算交易成本（手续费 + 滑点），返回总费用（元）"""
    if shares <= 0 or price <= 0:
        return 0.0

    amt = shares * price
    asset_type = _classify_asset_type(code)
    trading_cfg = config_manager.load_config('trading')
    comm_cfg = trading_cfg.get('commission', trading_cfg.get('commission', {}))

    # 手续费
    if asset_type in comm_cfg:
        cfg = comm_cfg[asset_type]
        rate = cfg.get('buy_rate' if side == 'buy' else 'sell_rate', 0.0003)
        fee = amt * rate
        min_fee = cfg.get('min_fee', 5.0)
        comm_fee = max(fee, min_fee)
    else:
        comm_fee = max(amt * 0.0003, 5.0) if side == 'buy' else amt * 0.00075

    # 滑点
    slip_cfg = trading_cfg.get('slippage', {})
    if price > 100:
        slip_per_share = slip_cfg.get('high_price', 0.05)
    elif price > 10:
        slip_per_share = slip_cfg.get('mid_price', 0.02)
    else:
        slip_per_share = slip_cfg.get('low_price', 0.01)
    slip_cost = abs(slip_per_share * shares)

    return comm_fee + slip_cost


class ProgressIndicator:
    """实时进度指示器"""

    def __init__(self, task_name: str, total_steps: int = 100):
        self.task_name = task_name
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
        self._spinner_chars = ['|', '/', '-', '\\']
        self._spinner_index = 0

    def update(self, step: int, message: str = ""):
        """更新进度"""
        self.current_step = min(step, self.total_steps)
        elapsed = time.time() - self.start_time
        progress = (self.current_step / self.total_steps) * 100

        bar_length = 20
        filled = int(bar_length * (self.current_step / self.total_steps))
        bar = '█' * filled + '░' * (bar_length - filled)

        self._spinner_index = (self._spinner_index + 1) % 4
        spinner = self._spinner_chars[self._spinner_index]

        eta = "计算中..."
        if self.current_step > 0:
            eta_seconds = (elapsed / self.current_step) * (self.total_steps - self.current_step)
            if eta_seconds < 60:
                eta = f"ETA: {int(eta_seconds)}s"
            else:
                eta = f"ETA: {int(eta_seconds / 60)}m"

        print(f"\r{spinner} {self.task_name}: [{bar}] {progress:.1f}% {eta} {message}", end='')
        sys.stdout.flush()

    def complete(self, message: str = "完成"):
        """标记完成"""
        elapsed = time.time() - self.start_time
        print(f"\r✓ {self.task_name}: [{''.join(['█'] * 20)}] 100% 耗时: {elapsed:.2f}s {message}")
        sys.stdout.flush()
