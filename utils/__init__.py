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
from .timesfm_predictor import (
    TimesFMPredictor,
    generate_signal_report,
    PORTFOLIO_SYMBOLS,
    CATEGORY_NAMES,
)
from .signal_fusion import (
    SignalFusionEngine,
    SignalResult,
    FusedSignal,
    get_fusion_engine,
    get_consensus_action,
)
from .ai_coordinator import (
    AICoordinator,
    TaskType,
    Priority,
    get_ai_coordinator,
)
from .signal_audit import (
    SignalAuditor,
    get_signal_auditor,
)
from .ml_labeling import (
    TripleBarrierLabeler,
    MetaLabeler,
    BarrierConfig,
    LabelResult,
    batch_label,
)
from .ml_predictor import StackingPredictor

# Optuna 训练器条件导入（需要 optuna 库）
try:
    from .ml_optuna_trainer import OptunaModelTrainer, run_optuna_training, walk_forward_split
    _has_optuna_trainer = True
except ImportError:
    OptunaModelTrainer = None
    run_optuna_training = None
    walk_forward_split = None
    _has_optuna_trainer = False

# v5.7 Phase 3: ConfigHub + MLflow
from .config_hub import ConfigHub, get_config_hub, PortfolioConfig, AssetParams

# MLflow 条件导入
try:
    from .mlflow_tracker import MLflowTracker, create_tracker
    _has_mlflow = True
except ImportError:
    MLflowTracker = None
    create_tracker = None
    _has_mlflow = False

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
    # TimesFM 预测
    'TimesFMPredictor', 'generate_signal_report', 'PORTFOLIO_SYMBOLS',
    'CATEGORY_NAMES',
    # v5.7 新模块
    'SignalFusionEngine', 'SignalResult', 'FusedSignal',
    'get_fusion_engine', 'get_consensus_action',
    'AICoordinator', 'TaskType', 'Priority', 'get_ai_coordinator',
    # v5.7 Phase 2
    'SignalAuditor', 'get_signal_auditor',
    # v5.7 Phase 2: ML 模型升级
    'TripleBarrierLabeler', 'MetaLabeler', 'BarrierConfig', 'LabelResult', 'batch_label',
    'StackingPredictor',
    # v5.7 Phase 3: 工程化
    'ConfigHub', 'get_config_hub', 'PortfolioConfig', 'AssetParams',
    'MLflowTracker', 'create_tracker',
]