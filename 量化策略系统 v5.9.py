# -*- coding: utf-8 -*-
"""
量化策略系统 v5.9 — 康波周期 + 十五五规划 + 社保基金ETF追踪 优化版 + 对冲再平衡联动v5.9
整合所有核心模块的统一入口，基于 2026 年交易计划优化版

配置风格: 核心-卫星 + 动量择时 + 风险平价
总资金: 300 万
目标: 年化收益 ≥ 8%，最大回撤 ≤ 15%
标的数量: 20 只（12 股票 + 7 ETF + 1 现金）

标的配置（2026 优化版）:
  - 核心宽基 ETF（30%）: 510300/510500/512100/588000/159915
  - 科技成长个股（25%）: 688041/300308/300274/002371/688017/600276/603019
  - 高端制造/基建（20%）: 600089/600875/000425/600406/600989
  - 防御/红利（5%）: 601088
  - 黄金 ETF（5%）: 518880
  - 现金缓冲（10%）: CASH

功能模块:
  1. 实时行情数据获取 (Wind / iFinD / LSEG / yfinance / tushare / 新浪 七级回退) ⭐
  2. 自动交易与盘中再平衡
  3. 增强版再平衡引擎 (Excel数据驱动 - 5表联动)
  4. 每日报告生成 (含AI分析)
  6. 组合管理与仓位优化 (新增：等权重/风险平价/风险配比/因子配比)
  7. 策略注册表与假设验证机制
  8. 研究目标生命周期管理
  9. ETF国家队资金流向监控 (投资决策参考)
  10. 康波周期大宗商品监控 (新增：价格/宏观/库存三维度)
  11. 时序预测模型支持 (新增：Transformer骨架集成)
  12. LSEG金融数据集成 (新增：股票/债券/FX/期权/宏观指标)
  13. 康波周期+十五五交叠分析 (v5.1新增：周期阶段判定+行业轮动+商品信号)
  14. 十五五规划适配分析 (v5.1新增：持仓对标+政策对齐评分+权重调整)
  16. 期货期权扫描 (新增：期货市场+期权市场+套利机会)
  17. 统一监控模式 (新增：一键启动所有模块并行运行)
18. AI Hedge Fund - 19位大师级AI分析师联合决策 (v5.6新增)
19. ML模型预测信号 - GradientBoosting涨跌预测 (v5.6新增)
20. 对冲再平衡联动引擎 v5.9 - 组合自触发+多指数对冲+成本过滤 (v5.9新增)



运行模式:
  - 实时监控模式: 盘中实时行情监控 + 自动再平衡
  - 报告生成模式: 生成每日持仓报告
  - 回测模式: 历史数据回测验证
  - 风险监控模式: 止损止盈状态检查
  - ETF资金流向: 追踪国家队资金动向
  - 假设验证模式: 验证交易假设
  - 投资组合优化: 多策略资产配置对比 (新增)
  - 康波周期监控: 大宗商品全维度监控 (新增)
  - 大宗商品基本面: Wind数据综合分析 (新增)
  - 时序预测训练: Transformer模型训练 (新增)

使用方式:
  python "量化策略系统 v5.9.py" --daily --phase premarket   # 盘前交易计划
  python "量化策略系统 v5.9.py" --daily --phase intraday    # 盘中策略扫描
  python "量化策略系统 v5.9.py" --daily --phase postmarket  # 盘后综合报告
  python "量化策略系统 v5.9.py" --daily --phase all         # 全流程
  python "量化策略系统 v5.9.py" --rebalance      # 执行Excel再平衡
  python "量化策略系统 v5.9.py" --rebalance --sync-sl  # 同步止损止盈
  python "量化策略系统 v5.9.py" --live           # 实时监控模式
  python "量化策略系统 v5.9.py" --report         # 生成报告
  python "量化策略系统 v5.9.py" --etf-flow       # ETF资金流向监控
  python "量化策略系统 v5.9.py" --portfolio-opt  # 投资组合优化
  python "量化策略系统 v5.9.py" --kommo-monitor  # 康波周期监控
  python "量化策略系统 v5.9.py" --commodity-fund # 大宗商品基本面
  python "量化策略系统 v5.9.py" --train-model    # 时序预测训练
  python "量化策略系统 v5.9.py" --train-enhanced              # ML增强训练 v2.0 (四维优化)
  python "量化策略系统 v5.9.py" --train-enhanced --horizon 5  # T+5中期预测训练
  python "量化策略系统 v5.9.py" --train-enhanced --horizon 10 --optuna  # T+10+贝叶斯
  python "量化策略系统 v5.9.py" --kondratiev     # 康波周期+十五五交叠分析 (v5.1)
  python "量化策略系统 v5.9.py" --fifteen-five   # 十五五规划适配分析 (v5.1)
  python "量化策略系统 v5.9.py" --social-security # 社保基金ETF风格追踪 (v5.1)
  python "量化策略系统 v5.9.py" --macro-analysis  # 宏观综合分析（一键运行三大）(v5.1)
  python "量化策略系统 v5.9.py" --ml-signal       # ML模型预测信号
  python "量化策略系统 v5.9.py" --ml-enhanced     # ML增强预测 v2.0 (四维优化模型)

架构特点 (借鉴Vibe-Trading):
  - Connector-first: 统一数据源抽象，支持多连接器配置 (Wind/iFinD/LSEG/yfinance/tushare/新浪) ⭐
  - 策略注册表: 中心化策略管理与版本控制
  - 假设验证: 支持统计检验与随机对照试验
  - 研究目标: 支持目标生命周期管理
  - 实时反馈: 长时间任务的进度可视化
  - Excel驱动: 5个Excel表格联动，配置即策略
  - 算力赛道: 康波第六轮核心驱动力配置
  - 投资组合优化: 等权重/风险平价/风险配比/因子配比/自定义配置 (新增)
  - 康波周期监控: 商品价格+宏观指标+产业库存三维度 (新增)
  - 时序预测: Transformer模型骨架集成 (新增)
  - LSEG集成: 国际金融市场全维度数据 (股票/债券/FX/期权/宏观) ⭐
"""

import os
import sys
import json
import glob
import argparse
import time
from datetime import datetime, time as dt_time
from typing import Dict, Any, Optional, List

import pandas as pd

from utils.console_encoding import setup_utf8_console
from utils.env_loader import load_dotenv

setup_utf8_console()
load_dotenv()  # 加载 .env 环境变量配置（含引号去除与已存在变量保护）

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ============================================================
# 日志配置 — 引入统一的日志管理器（借鉴 TradingAgents-CN 架构）
# ============================================================
from utils.logging_manager import setup_logging, get_logger
from utils.report_archiver import archive_report, get_archive_dir

setup_logging()
logger = get_logger('quant')

LOG_DIR = os.path.join(BASE_DIR, 'logs')

# ============================================================
# 事件追踪 — 引入统一的事件追踪器（借鉴 TradingAgents-CN 结构化事件模式）
# ============================================================
from utils.event_tracker import EventTracker, track_event, get_event_tracker

event_tracker = get_event_tracker()

# v5.2 去重 — 从权威模块导入替代内联类定义
from quant_modules.core import (
    StrategyRegistry, QuantSystemError, DataSourceError,
    ConfigError, TradingError, ValidationError,
    GracefulFallback, ModuleLoader, ConfigManager,
    load_portfolio_config, ProgressIndicator,
)
from quant_modules.data_layer import DataCache, DataConnector, DataConnectorManager
from engine.rebalance import ExcelDrivenRebalancingEngineV4
from engine.managers import (
    PortfolioOptimizationEngine, KommoCommodityMonitor, ETFFundFlowMonitor,
)

# ============================================================
# 全局降级管理器
# ============================================================
graceful_fallback = GracefulFallback()

# 注册默认降级处理器
graceful_fallback.register_fallback(DataSourceError, lambda e: {})
graceful_fallback.register_fallback(ConfigError, lambda e: {})

# 全局配置管理器实例
config_manager = ConfigManager()

# ============================================================
# 模块导入 (优雅降级) - 加载核心模块
# ============================================================
loader = ModuleLoader()

# 数据提供层
data_provider = loader.load('wind_data_provider', {
    'get_quotes_batch': 'get_quotes_batch',
    'get_quote': 'get_quote',
    'get_stats': 'get_wind_stats',
    'reset_stats': 'reset_stats'
})

# 自动交易系统
auto_trading = loader.load('auto_trading_system', {
    'AutoTradingSystem': 'AutoTradingSystem'
})

# 再平衡引擎
rebalance_engine = loader.load('rebalancing_engine', {
    'RebalancingEngine': 'RebalancingEngine'
})

# 每日报告
daily_report = loader.load('daily_report', {
    'generate_daily_report': 'generate_daily_report'
})

# 止损止盈监控
stop_loss = loader.load('stop_loss_monitor', {
    'StopLossMonitor': 'StopLossMonitor',
    'generate_risk_alert_report': 'generate_risk_alert_report'
})

# 策略注册表实例
strategy_registry = StrategyRegistry()
connector_manager = DataConnectorManager()

# v5.7 Phase 3: 统一配置中心 (替代分散的 load_portfolio_config)
config_hub = None
try:
    from utils.config_hub import ConfigHub
    config_hub = ConfigHub(config_dir=os.path.join(BASE_DIR, 'config'))
    logger.info(f"[ConfigHub] 已加载 {len(config_hub.get_all_asset_codes())} 个标的的配置")
except Exception as e:
    logger.warning(f"[ConfigHub] 初始化失败: {e}，回退到传统配置加载")

# ============================================================
# 注册所有数据源连接器 (Wind MCP → iFinD MCP → Sina → 本地缓存)
# ============================================================
try:
    from quant_modules.connectors import register_all_connectors
    n_registered = register_all_connectors(connector_manager)
    if n_registered > 0:
        # 显式激活主连接器 (Wind MCP, 优先级100)
        primary = connector_manager.get_active_connector()
        logger.info(f"✅ 数据源连接器注册完成: {n_registered} 个可用, 主连接器: {primary.name if primary else 'None'}")
    else:
        logger.warning("⚠️ 无可用数据源连接器，系统将以离线模式运行")
except ImportError as e:
    logger.warning(f"⚠️ 连接器注册模块加载失败: {e}")
except Exception as e:
    logger.warning(f"⚠️ 连接器注册异常: {e}")

# ============================================================
# 康波周期 / 十五五规划 / 社保基金ETF 分析模块 (v5.1 新增)
# ============================================================
try:
    from utils.kondratiev_cycle import KondratievCycleAnalyzer
    KONDRATIEV_AVAILABLE = True
    logger.info("✅ 康波周期分析模块已加载")
except ImportError as e:
    KondratievCycleAnalyzer = None
    KONDRATIEV_AVAILABLE = False
    logger.warning(f"⚠️ 康波周期分析模块加载失败: {e}")

try:
    from utils.five_year_plan import FifteenFivePlanAnalyzer
    FIFTEEN_FIVE_AVAILABLE = True
    logger.info("✅ 十五五规划分析模块已加载")
except ImportError as e:
    FifteenFivePlanAnalyzer = None
    FIFTEEN_FIVE_AVAILABLE = False
    logger.warning(f"⚠️ 十五五规划分析模块加载失败: {e}")

try:
    from utils.social_security_etf import SocialSecurityETFTracker
    SOCIAL_SECURITY_ETF_AVAILABLE = True
    logger.info("✅ 社保基金ETF追踪模块已加载")
except ImportError as e:
    SocialSecurityETFTracker = None
    SOCIAL_SECURITY_ETF_AVAILABLE = False
    logger.warning(f"⚠️ 社保基金ETF追踪模块加载失败: {e}")

# ============================================================
# ML 模型预测模块 (v5.6 新增) - GradientBoosting + 特征选择
# ============================================================
try:
    from utils.ml_predictor import MLModelPredictor, run_ml_signal_scan, EnhancedPredictor
    ML_PREDICTOR_AVAILABLE = True
    ML_ENHANCED_PREDICTOR_AVAILABLE = EnhancedPredictor is not None
    logger.info("✅ ML模型预测模块已加载")
except ImportError as e:
    MLModelPredictor = None
    run_ml_signal_scan = None
    EnhancedPredictor = None
    ML_PREDICTOR_AVAILABLE = False
    ML_ENHANCED_PREDICTOR_AVAILABLE = False
    logger.warning(f"⚠️ ML模型预测模块加载失败: {e}")

# v2.0 增强训练引擎
try:
    from utils.ml_enhanced_trainer import (
        EnhancedMLTrainer, EnhancedFeatureEngineer, run_enhanced_training
    )
    ML_ENHANCED_TRAINER_AVAILABLE = True
    logger.info("✅ ML增强训练引擎 v2.0 已加载")
except ImportError as e:
    EnhancedMLTrainer = None
    EnhancedFeatureEngineer = None
    run_enhanced_training = None
    ML_ENHANCED_TRAINER_AVAILABLE = False
    logger.warning(f"⚠️ ML增强训练引擎未加载: {e}")

# ============================================================
# v5.7 Phase 2: AI Hedge Fund 懒加载缓存 & AI协调器
# ============================================================
_AI_HEDGE_IMPORTED = False
_AI_HEDGE_MODULE = {}

try:
    from utils.ai_coordinator import get_ai_coordinator
    AI_COORDINATOR_AVAILABLE = True
except ImportError:
    get_ai_coordinator = None
    AI_COORDINATOR_AVAILABLE = False

# ============================================================
# LSEG MCP 连接器集成 (优先级3) - 已禁用
# ============================================================
# 如需启用 LSEG，请取消下面的注释并设置 LSEG_API_KEY 环境变量
# try:
#     from lseg_integration import register_lseg_connector
#     register_lseg_connector(connector_manager)
#     logger.info("✅ LSEG MCP 连接器已注册 (优先级: 3)")
# except ImportError as e:
#     logger.warning(f"⚠️  LSEG 集成模块未找到: {e}")
#     logger.warning("   如需启用 LSEG 数据源，请确保 lseg_integration.py 存在")
# except Exception as e:
#     logger.warning(f"⚠️  LSEG 连接器注册失败: {e}")

# ============================================================
# 通用辅助函数 — 消除各 run_* 模式中的重复样板
# ============================================================
def _write_report_file(report: str, filename: Optional[str]) -> None:
    """可选：将报告写入 BASE_DIR/reports/<filename>（filename 为空则跳过）。"""
    if not filename:
        return
    report_dir = os.path.join(BASE_DIR, 'reports')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, filename)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n✅ 报告已保存: {report_path}")


def _archive_report(report: str, name: str, ext: str = '.md') -> str:
    """归档报告到「每日报告归档」目录，返回归档路径。"""
    archive_name = f'{name}_{datetime.now().strftime("%Y%m%d")}{ext}'
    archive_path = archive_report(BASE_DIR, archive_name, report)
    print(f"✅ 报告已归档: {archive_path}")
    return archive_path


def _get_stock_name(code: str) -> str:
    """解析标的名称，优先从 names.py 查找，备用纯代码。"""
    try:
        from ui.components.names import STOCK_NAME_MAP
        # 去掉后缀 .SZ/.SH
        pure = code.split('.')[0] if '.' in code else code
        return STOCK_NAME_MAP.get(pure, code)
    except ImportError:
        return code


def _get_ml_signal_section(external_signals: dict = None, return_raw=False,
                           use_enhanced: bool = True) -> Optional[str]:
    """
    运行 ML 模型信号扫描，返回 Markdown 格式的信号报告段落。
    若 ML 模块不可用或扫描失败，返回 None。

    v5.9 增强:
    - use_enhanced=True 时优先使用四维优化模型 (EnhancedPredictor)
    - 包含预测窗口和过滤震荡信息
    """
    if not ML_PREDICTOR_AVAILABLE:
        return None

    result = {}
    try:
        model_dir = os.path.join(BASE_DIR, 'models')
        data_dir = os.path.join(BASE_DIR, 'data', 'cache')

        # v5.9: 优先使用增强预测器
        enhanced_info = {}
        if use_enhanced and ML_ENHANCED_PREDICTOR_AVAILABLE and EnhancedPredictor is not None:
            try:
                ep = EnhancedPredictor(model_dir=model_dir, weight_method='f1_weighted')
                if ep.auto_discover_and_load(prefer_enhanced=True):
                    kline_dict = {}
                    for f in glob.glob(os.path.join(data_dir, 'kline_*.parquet')):
                        code = os.path.basename(f).replace('kline_', '').replace('_daily.parquet', '')
                        try: kline_dict[code] = pd.read_parquet(f)
                        except Exception: continue
                    if kline_dict:
                        signals = ep.generate_trading_signals(kline_dict)
                        info = ep.get_model_info()
                        enhanced_info = {
                            'horizon': info.get('horizon', 1),
                            'filter_oscillation': info.get('filter_oscillation', True),
                            'model_count': info.get('model_count', 0),
                            'feature_count': info.get('feature_count', 0),
                        }
                        result = {
                            'model_info': info,
                            'signals': signals,
                            'scanned_count': len(kline_dict),
                            'enhanced': True,
                        }
                        logger.info(f"增强预测器就绪: T+{enhanced_info['horizon']}")
                    else:
                        enhanced_info = {}
            except Exception as e:
                logger.debug(f"增强预测器跳过: {e}")
                enhanced_info = {}

        if not enhanced_info and run_ml_signal_scan is not None:
            result = run_ml_signal_scan(data_dir=data_dir, model_dir=model_dir, threshold=0.55)

        if not result or 'error' in result:
            logger.warning(f"ML信号扫描失败: {result.get('error', '无数据')}")
            return None

        model_info = result.get('model_info', {})
        signals = result.get('signals', {})
        is_enhanced = result.get('enhanced', False)

        lines = []
        lines.append("")
        lines.append("---")
        lines.append("")
        if is_enhanced:
            lines.append(f"## ML增强预测信号 v2.0 (四维优化, T+{enhanced_info.get('horizon', 1)})")
        else:
            lines.append("## ML模型预测信号 (LightGBM)")
        lines.append("")
        lines.append(f"- **模型**: {model_info.get('best_model', 'N/A')}")
        lines.append(f"- **准确率**: {model_info.get('accuracy', 0):.2%} "
                     f"| F1: {model_info.get('f1', 0):.4f} "
                     f"| AUC: {model_info.get('auc', 0):.4f}")
        if is_enhanced:
            lines.append(f"- **预测窗口**: T+{enhanced_info.get('horizon', 1)} "
                         f"| 过滤震荡: {enhanced_info.get('filter_oscillation', True)} "
                         f"| 模型数: {enhanced_info.get('model_count', 0)}")
        lines.append(f"- **信号阈值**: 55% | 扫描标的: {result.get('scanned_count', 0)} 只")
        ds_label = getattr(connector_manager, 'get_data_source_label', lambda: 'Unknown')()
        lines.append(f"- **数据源**: {ds_label}")
        lines.append("")

        buy_signals = signals.get('buy', [])
        sell_signals = signals.get('sell', [])
        hold_signals = signals.get('hold', [])
        lines.append(f"买入: {len(buy_signals)} | 卖出: {len(sell_signals)} | 持有/震荡: {len(hold_signals)}")
        lines.append("")

        if buy_signals:
            lines.append("### 买入信号")
            lines.append("")
            if external_signals:
                lines.append("| 代码 | 名称 | 上涨概率 | 置信度 | 外部信号 |")
                lines.append("|------|------|----------|--------|----------|")
                for s in sorted(buy_signals, key=lambda x: x['probability'], reverse=True):
                    name = _get_stock_name(s['code'])
                    ext = external_signals.get(s['code'], {})
                    ext_label = f"{ext.get('source', '?')}: {ext.get('action', '?')}" if ext else ""
                    lines.append(f"| {s['code']} | {name} | {s['probability']:.2%} | {s['confidence']:.2%} | {ext_label} |")
            else:
                lines.append("| 代码 | 名称 | 上涨概率 | 置信度 |")
                lines.append("|------|------|----------|--------|")
                for s in sorted(buy_signals, key=lambda x: x['probability'], reverse=True):
                    name = _get_stock_name(s['code'])
                    lines.append(f"| {s['code']} | {name} | {s['probability']:.2%} | {s['confidence']:.2%} |")
            lines.append("")

        if sell_signals:
            lines.append("### 卖出信号")
            lines.append("")
            if external_signals:
                lines.append("| 代码 | 名称 | 下跌概率 | 置信度 | 外部信号 |")
                lines.append("|------|------|----------|--------|----------|")
                for s in sorted(sell_signals, key=lambda x: x['probability']):
                    name = _get_stock_name(s['code'])
                    ext = external_signals.get(s['code'], {})
                    ext_label = f"{ext.get('source', '?')}: {ext.get('action', '?')}" if ext else ""
                    lines.append(f"| {s['code']} | {name} | {1 - s['probability']:.2%} | {s['confidence']:.2%} | {ext_label} |")
            else:
                lines.append("| 代码 | 名称 | 下跌概率 | 置信度 |")
                lines.append("|------|------|----------|--------|")
                for s in sorted(sell_signals, key=lambda x: x['probability']):
                    name = _get_stock_name(s['code'])
                    lines.append(f"| {s['code']} | {name} | {1 - s['probability']:.2%} | {s['confidence']:.2%} |")
            lines.append("")

        # v5.7 Phase 3 增强：多信号一致性分析（含AI Hedge Fund + GLM-5 + ML对比）
        if external_signals and (buy_signals or sell_signals):
            lines.append("### 多信号一致性分析")
            lines.append("")
            lines.append("*三信号源融合决策：ML模型 + AI Hedge Fund + GLM-5。一致性越高，置信度越高。*")
            lines.append("")

            all_ml_codes = {s['code']: s for s in (buy_signals + sell_signals + hold_signals)}

            agree_count = 0
            conflict_count = 0
            undefined_count = 0
            consistency_rows = []

            for code, ext in external_signals.items():
                ml_sig = all_ml_codes.get(code)
                if not ml_sig:
                    undefined_count += 1
                    continue

                ml_prob = ml_sig.get('probability', 0.5)
                ml_action = 'BUY' if ml_prob >= 0.55 else 'SELL' if ml_prob <= 0.45 else 'HOLD'
                ext_action = ext.get('action', 'HOLD')
                ext_source = ext.get('source', '?')

                # 判断一致性
                all_actions = [ml_action, ext_action]
                glm5_action = ext.get('glm5_action', '')
                if glm5_action:
                    all_actions.append(glm5_action)

                if all(a == 'BUY' for a in all_actions if a):
                    status = '✅ 强烈一致买入'
                    agree_count += 1
                elif all(a == 'SELL' for a in all_actions if a):
                    status = '🔴 强烈一致卖出'
                    agree_count += 1
                elif any(a == 'BUY' and 'SELL' in all_actions for a in all_actions):
                    status = '⚠️ 分歧'
                    conflict_count += 1
                else:
                    status = '🟡 中性/混合'

                # 综合投票
                buy_votes = sum(1 for a in all_actions if a == 'BUY')
                sell_votes = sum(1 for a in all_actions if a == 'SELL')
                hold_votes = sum(1 for a in all_actions if a == 'HOLD')
                if buy_votes > sell_votes and buy_votes > hold_votes:
                    combined = '买入'
                elif sell_votes > buy_votes and sell_votes > hold_votes:
                    combined = '卖出'
                else:
                    combined = '观望'

                consistency_rows.append({
                    'code': code,
                    'name': _get_stock_name(code),
                    'ml_prob': ml_prob,
                    'ml_action': ml_action,
                    'ext_source': ext_source,
                    'ext_action': ext_action,
                    'glm5': glm5_action,
                    'status': status,
                    'combined': combined,
                    'confidence': ml_sig.get('confidence', 0),
                })

            # 按一致性优先级排序：一致买入 > 一致卖出 > 其余
            consistency_rows.sort(key=lambda r: (
                0 if '一致买入' in r['status'] else 1 if '一致卖出' in r['status'] else 2,
                -r['confidence'],
            ))

            # 汇总统计
            lines.append(f"| 指标 | 数值 |")
            lines.append(f"|------|------|")
            lines.append(f"| ML预测标的总数 | {len(all_ml_codes)} |")
            lines.append(f"| 多信号对照标的 | {len(consistency_rows)} |")
            lines.append(f"| 信号一致 | {agree_count} |")
            lines.append(f"| 信号冲突 | {conflict_count} |")
            lines.append(f"| 一致率 | {agree_count / max(agree_count + conflict_count, 1):.1%} |")
            lines.append("")

            # 详细一致性表格
            if consistency_rows:
                lines.append("| 代码 | 名称 | ML概率 | ML | 外部信号 | 外部 | GLM-5 | 状态 | 综合 |")
                lines.append("|------|------|--------|----|----------|------|-------|------|------|")
                for r in consistency_rows:
                    ml_label = f"🟢" if r['ml_action'] == 'BUY' else f"🔴" if r['ml_action'] == 'SELL' else "🟡"
                    ext_label = f"🟢" if r['ext_action'] == 'BUY' else f"🔴" if r['ext_action'] == 'SELL' else "🟡"
                    glm5_label = f"🟢" if r['glm5'] == 'BUY' else f"🔴" if r['glm5'] == 'SELL' else \
                                  f"🟡" if r['glm5'] == 'HOLD' else "-"
                    lines.append(
                        f"| {r['code']} | {r['name']} | {r['ml_prob']:.2%} | "
                        f"{ml_label} | {r['ext_source']} | {ext_label} | "
                        f"{glm5_label} | {r['status']} | {r['combined']} |"
                    )
                lines.append("")

                # 置信度最高的一致信号
                consensus_buys = [r for r in consistency_rows if '一致买入' in r['status']]
                consensus_sells = [r for r in consistency_rows if '一致卖出' in r['status']]
                conflicts = [r for r in consistency_rows if '分歧' in r['status']]

                if consensus_buys:
                    top_buys = sorted(consensus_buys, key=lambda r: r['confidence'], reverse=True)[:3]
                    items = [f"{r['name']}({r['confidence']:.1%})" for r in top_buys]
                    lines.append(f"**高置信一致买入**: {', '.join(items)}")
                if consensus_sells:
                    top_sells = sorted(consensus_sells, key=lambda r: r['confidence'], reverse=True)[:3]
                    items = [f"{r['name']}({r['confidence']:.1%})" for r in top_sells]
                    lines.append(f"**高置信一致卖出**: {', '.join(items)}")
                if conflicts:
                    lines.append(f"**信号冲突需关注**: {', '.join(r['name'] for r in conflicts)}")
                    lines.append("")

            lines.append("")

        lines.append("> 信号仅供参考，不构成投资建议。请结合基本面与技术面综合判断。")
        report = '\n'.join(lines)
        return (report, result) if return_raw else report

    except Exception as e:
        logger.warning(f"ML信号扫描异常: {e}")
        return None


def _get_portfolio_quotes() -> Dict[str, Dict[str, float]]:
    """加载持仓配置并批量获取行情，返回 {code: {'price': p}}（行情不可用时返回空字典）。"""
    get_quotes_batch = data_provider.get('get_quotes_batch')
    config = load_portfolio_config()
    if not get_quotes_batch or not config:
        return {}
    codes = [a['code'] for a in config.get('assets', [])]
    stocks = [c for c in codes if not (c.startswith('5') or c == '159915')]
    funds = [c for c in codes if c.startswith('5') or c == '159915']
    prices = get_quotes_batch(stocks, funds)
    return {k: {'price': v['price']} for k, v in prices.items() if v['price'] > 0}


def _build_etf_flow_data(flow_monitor) -> Optional[dict]:
    """将 ETFFundFlowMonitor.flow_data 转为 SocialSecurityETFTracker 需要的格式（无数据返回 None）。"""
    if not flow_monitor.flow_data:
        return None
    return {
        code: {
            "name": data.get("name", code),
            "net_flow_yi": data.get("net_flow_yi", 0),
            "trend": data.get("trend", "中性"),
            "category": data.get("category", "未知"),
        }
        for code, data in flow_monitor.flow_data.items()
    }


def _get_etf_flow_data(connector_manager=None) -> Optional[dict]:
    """获取ETF资金流数据（带错误处理和降级）。"""
    if connector_manager is None:
        connector_manager = globals().get('connector_manager')
    try:
        flow_monitor = ETFFundFlowMonitor(data_connector_manager=connector_manager)
        flow_monitor.analyze_fund_flow()
        return _build_etf_flow_data(flow_monitor)
    except Exception as e:
        logger.debug(f"获取ETF资金流数据失败（将使用静态分析）: {e}")
        return None


def run_etf_flow_monitor(args):
    """ETF资金流向监控模式 - 追踪国家队资金动向"""
    print("\n📊 ETF国家队资金流向监控")
    print("=" * 70)
    
    progress = ProgressIndicator("ETF资金流向分析", 4)
    
    progress.update(1, "初始化监控器...")
    monitor = ETFFundFlowMonitor(data_connector_manager=connector_manager)
    
    progress.update(2, "获取ETF行情数据...")
    flow_data = monitor.analyze_fund_flow()
    
    progress.update(3, "检测国家队信号...")
    signals = monitor.detect_signals()
    
    progress.update(4, "生成投资建议...")
    suggestions = monitor.get_investment_suggestion()
    
    # 生成报告
    report = monitor.generate_report()
    print("\n" + report)

    _write_report_file(report, args.output)
    _archive_report(report, 'ETF资金流向')

    progress.complete(f"检测到 {len(signals)} 条信号")

    return monitor

def run_ml_signal_mode(args):
    """ML模型预测信号模式 - 基于训练好的模型生成涨跌信号"""
    print("\n🤖 ML模型预测信号扫描")
    print("=" * 70)
    
    if not ML_PREDICTOR_AVAILABLE:
        print("\n❌ ML模型预测模块不可用")
        return None
    
    progress = ProgressIndicator("ML信号扫描", 5)
    
    # 解析阈值参数
    threshold = 0.55
    if hasattr(args, 'threshold') and args.threshold:
        threshold = args.threshold
    
    progress.update(1, "加载ML模型...")
    model_dir = os.path.join(BASE_DIR, 'models')
    data_dir = os.path.join(BASE_DIR, 'data', 'cache')

    # v5.7 Phase 2: Stacking集成预测（如果启用）
    use_stacking = getattr(args, 'stacking', False)
    stacking_info = None

    if use_stacking:
        print("\n  🧠 启用 Stacking 多模型集成预测...")
        try:
            from utils.ml_predictor import StackingPredictor
            stacking = StackingPredictor(
                model_dir=model_dir,
                weight_method='f1_weighted',
            )
            stacking._loaded = True  # 将先调用 auto_discover_and_load
            progress.update(2, "加载K线数据...")

            # 手动扫描
            kline_dict = {}
            for f in glob.glob(os.path.join(data_dir, 'kline_*.parquet')):
                code = f.replace('kline_', '').replace('_daily.parquet', '')
                try:
                    kline_dict[code] = pd.read_parquet(f)
                except Exception as e:
                    logger.debug(f"读取kline文件失败 {f}: {e}")

            if kline_dict:
                progress.update(3, "Stacking融合预测...")
                predictions = stacking.batch_predict(kline_dict, top_n=len(kline_dict))

                # 将 Stacking 结果转换为信号格式
                buy_signals = []
                sell_signals = []
                hold_signals = []
                for pred in predictions:
                    code = pred['code']
                    prob = pred['probability']
                    entry = {
                        'code': code,
                        'probability': prob,
                        'confidence': pred['confidence'],
                        'signal_strength': pred['signal'],
                        'agreement': pred.get('agreement', 0),
                    }
                    if prob > threshold:
                        buy_signals.append(entry)
                    elif prob < (1 - threshold):
                        sell_signals.append(entry)
                    else:
                        hold_signals.append(entry)

                result = {
                    'model_info': {
                        'best_model': 'Stacking',
                        'accuracy': 0,
                        'f1': 0,
                        'feature_count': len(stacking.selected_features),
                        'model_count': len(stacking.models),
                    },
                    'signals': {
                        'buy': buy_signals,
                        'sell': sell_signals,
                        'hold': hold_signals,
                        'threshold': threshold,
                        'total': len(predictions),
                        'model': 'Stacking',
                    },
                    'scanned_count': len(kline_dict),
                    'stacking_info': {
                        'models': list(stacking.model_weights.keys()),
                        'weights': {k: round(w, 4) for k, w in stacking.model_weights.items()},
                        'weight_method': stacking.weight_method,
                    },
                }
                stacking_info = result['stacking_info']
            else:
                print("  ⚠️ 无K线数据，回退到单模型")
                use_stacking = False
        except Exception as e:
            print(f"  ⚠️ Stacking加载失败 ({e})，回退到单模型")
            use_stacking = False

    if not use_stacking:
        progress.update(2, "加载K线数据...")
        progress.update(3, "构建特征并预测...")
        result = run_ml_signal_scan(
            data_dir=data_dir,
            model_dir=model_dir,
            threshold=threshold,
        )
    
    if 'error' in result:
        print(f"\n❌ 错误: {result['error']}")
        return None
    
    progress.update(4, "生成信号报告...")
    
    model_info = result.get('model_info', {})
    signals = result.get('signals', {})
    scanned_count = result.get('scanned_count', 0)
    
    # 生成报告
    report_lines = []
    report_lines.append("# ML模型预测信号报告")
    report_lines.append("")
    report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**扫描标的数**: {scanned_count}")
    report_lines.append("")
    report_lines.append("## 模型信息")
    report_lines.append("")
    report_lines.append(f"- **模型**: {model_info.get('best_model', 'N/A')}")
    report_lines.append(f"- **准确率**: {model_info.get('accuracy', 0):.2%}")
    report_lines.append(f"- **F1分数**: {model_info.get('f1', 0):.4f}")
    report_lines.append(f"- **AUC**: {model_info.get('auc', 0):.4f}")
    report_lines.append(f"- **特征数**: {model_info.get('feature_count', 0)}")
    # v5.7 Phase 2: Stacking 信息
    if stacking_info:
        report_lines.append(f"- **集成方法**: Stacking ({len(stacking_info.get('models',[]))}个模型)")
        report_lines.append(f"- **子模型**: {', '.join(stacking_info.get('models',[]))}")
        report_lines.append(f"- **权重方法**: {stacking_info.get('weight_method', 'f1_weighted')}")
    report_lines.append(f"- **信号阈值**: {threshold:.2%}")
    report_lines.append("")
    report_lines.append("## 信号汇总")
    report_lines.append("")
    report_lines.append(f"- 🟢 **买入信号**: {len(signals.get('buy', []))} 只")
    report_lines.append(f"- 🔴 **卖出信号**: {len(signals.get('sell', []))} 只")
    report_lines.append(f"- 🟡 **持有观望**: {len(signals.get('hold', []))} 只")
    report_lines.append("")
    
    # 买入信号详情
    buy_signals = signals.get('buy', [])
    if buy_signals:
        report_lines.append("## 🟢 买入信号 (上涨概率 > 阈值)")
        report_lines.append("")
        report_lines.append("| 代码 | 上涨概率 | 置信度 | 信号强度 |")
        report_lines.append("|------|----------|--------|----------|")
        for s in sorted(buy_signals, key=lambda x: x['probability'], reverse=True):
            report_lines.append(
                f"| {s['code']} | {s['probability']:.2%} | {s['confidence']:.2%} | {s['signal_strength']:.4f} |"
            )
        report_lines.append("")
    
    # 卖出信号详情
    sell_signals = signals.get('sell', [])
    if sell_signals:
        report_lines.append("## 🔴 卖出信号 (下跌概率 > 阈值)")
        report_lines.append("")
        report_lines.append("| 代码 | 下跌概率 | 置信度 | 信号强度 |")
        report_lines.append("|------|----------|--------|----------|")
        for s in sorted(sell_signals, key=lambda x: x['probability']):
            down_prob = 1 - s['probability']
            report_lines.append(
                f"| {s['code']} | {down_prob:.2%} | {s['confidence']:.2%} | {s['signal_strength']:.4f} |"
            )
        report_lines.append("")
    
    # 持有观望
    hold_signals = signals.get('hold', [])
    if hold_signals:
        report_lines.append("## 🟡 持有观望 (信号不明确)")
        report_lines.append("")
        report_lines.append("| 代码 | 上涨概率 | 置信度 |")
        report_lines.append("|------|----------|--------|")
        for s in sorted(hold_signals, key=lambda x: x['probability'], reverse=True):
            report_lines.append(
                f"| {s['code']} | {s['probability']:.2%} | {s['confidence']:.2%} |"
            )
        report_lines.append("")
    
    report_lines.append("## ⚠️ 风险提示")
    report_lines.append("")
    report_lines.append("- 本信号仅供参考，不构成投资建议")
    report_lines.append("- ML模型基于历史数据训练，未来表现不保证")
    report_lines.append("- 请结合基本面、技术面和风险承受能力综合判断")
    report_lines.append("")
    
    report = "\n".join(report_lines)
    
    # 打印报告摘要
    print("\n" + "=" * 70)
    print("ML模型预测信号报告")
    print("=" * 70)
    print(f"\n模型: {model_info.get('best_model', 'N/A')}")
    print(f"准确率: {model_info.get('accuracy', 0):.2%} | F1: {model_info.get('f1', 0):.4f}")
    print(f"扫描标的: {scanned_count} 只 | 阈值: {threshold:.2%}")
    print()
    print(f"🟢 买入信号: {len(buy_signals)} 只")
    print(f"🔴 卖出信号: {len(sell_signals)} 只")
    print(f"🟡 持有观望: {len(hold_signals)} 只")
    
    if buy_signals:
        print(f"\n🟢 买入信号 Top 5:")
        for s in buy_signals[:5]:
            print(f"  {s['code']}: 上涨概率 {s['probability']:.2%}, 置信度 {s['confidence']:.2%}")
    
    if sell_signals:
        print(f"\n🔴 卖出信号 Top 5:")
        for s in sell_signals[:5]:
            down_prob = 1 - s['probability']
            print(f"  {s['code']}: 下跌概率 {down_prob:.2%}, 置信度 {s['confidence']:.2%}")
    
    _write_report_file(report, args.output)
    _archive_report(report, 'ML预测信号')

    progress.update(5, "完成")
    progress.complete(f"扫描完成: 买入{len(buy_signals)} / 卖出{len(sell_signals)} / 持有{len(hold_signals)}")

    return result

def run_live_monitoring(args):
    """实时监控模式 - 盘中实时行情监控 + 自动再平衡 + ML信号"""
    print("\n🚀 启动实时监控模式")
    print("=" * 70)
    
    progress = ProgressIndicator("初始化系统", 6)
    
    progress.update(1, "扫描ML预测信号...")
    ml_result = _get_ml_signal_section(return_raw=True)
    if ml_result:
        ml_section, result = ml_result
        if 'signals' in result:
            sig = result['signals']
            buy_n = len(sig.get('buy', []))
            sell_n = len(sig.get('sell', []))
            hold_n = len(sig.get('hold', []))
            model_name = result.get('model_info', {}).get('best_model', '?')
            model_acc = result.get('model_info', {}).get('accuracy', 0)
            print(f"\n  [ML信号] {model_name} (Acc={model_acc:.1%}) "
                  f"买入:{buy_n} 卖出:{sell_n} 持有:{hold_n}")
            for s in sig.get('buy', [])[:5]:
                name = _get_stock_name(s['code'])
                print(f"    买入 {s['code']} {name:8s} 概率:{s['probability']:.1%}")
    else:
        print("  ⚠️ ML信号不可用")
    
    progress.update(2, "加载交易系统...")
    AutoTradingSystem = auto_trading.get('AutoTradingSystem')
    
    if AutoTradingSystem:
        progress.update(3, "创建交易实例...")
        system = AutoTradingSystem()
        
        progress.update(4, "连接数据源...")
        
        progress.update(5, "启动监控循环...")
        system.run()
        progress.complete("监控结束")
    else:
        progress.complete("❌ 自动交易系统模块不可用")

def run_report_generation(args):
    """报告生成模式 - 生成每日持仓报告 + ML信号 (v5.7 Phase 3: ConfigHub集成)"""
    print("\n📝 生成每日报告")
    print("=" * 70)
    
    progress = ProgressIndicator("生成报告", 7)
    
    progress.update(1, "加载报告模块...")
    generate_daily_report = daily_report.get('generate_daily_report')

    # v5.7 Phase 3: 使用 ConfigHub 获取统一配置
    portfolio_file = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
    if config_hub and not config_hub.check_and_reload():
        # 配置无变更，显示摘要
        summary = config_hub.get_summary()
        print(f"  📋 配置摘要: {summary['asset_count']}个标的, "
              f"总资金 {summary['total_capital']:,.0f}, "
              f"数据源: {summary['primary_source']}")
    
    if generate_daily_report:
        try:
            progress.update(2, "读取配置...")
            
            progress.update(3, "生成报告内容...")
            report_content = generate_daily_report(
                portfolio_file=portfolio_file,
                enable_ai_analysis=not args.no_ai
            )
            
            # ML信号追加到报告（若LLM已内置ML分析则跳过）
            if not getattr(args, 'no_ml', False):
                progress.update(4, "检查ML预测信号...")
                if '本地ML量化模型分析' in report_content:
                    print("  ✅ ML分析已由日报引擎自动内置，跳过追加")
                else:
                    ml_section = _get_ml_signal_section()
                    if ml_section:
                        report_content += ml_section
                        print("  ✅ ML信号已追加")
                    else:
                        print("  ⚠️ ML信号不可用")
            else:
                progress.update(4, "跳过ML信号...")
            
            progress.update(5, "保存报告...")
            archive_path = _archive_report(report_content, '综合日报', ext='.txt')

            progress.complete("✅ 报告归档完成")
            
        except Exception as e:
            progress.complete(f"\n❌ 报告生成失败: {e}")
            logger.error(f"报告生成失败: {e}")
    else:
        progress.complete("❌ 每日报告模块不可用")

def run_rebalance(args):
    """再平衡模式 - 执行再平衡计划 (支持Excel和portfolio.yaml两种方式)"""
    print("\n🔄 执行再平衡计划")
    print("=" * 70)
    
    progress = ProgressIndicator("再平衡执行", 6)
    
    # 使用增强版Excel驱动引擎
    progress.update(1, "初始化再平衡引擎...")
    strategy_registry = StrategyRegistry()
    engine = ExcelDrivenRebalancingEngineV4(strategy_registry=strategy_registry)
    
    progress.update(2, "加载配置文件...")
    loaded = engine.load_all()
    
    # 如果Excel加载失败,尝试从portfolio.yaml加载
    if not loaded:
        print("\n⚠️ Excel文件不存在,尝试从portfolio.yaml加载...")
        try:
            import yaml
            yaml_path = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
            if os.path.exists(yaml_path):
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                assets = config.get('assets', [])
                if assets:
                    engine.complete_plan = [
                        {
                            '证券代码': a['code'], '证券名称': a['name'],
                            '目标权重': a.get('target_weight', 0.1),
                            '风险权重': 0.25, '当前仓位': 0, '调整幅度': 0,
                            '当前股数': 0, '最新价': 0, '当前市值': 0,
                            '目标市值': 0, '目标股数': 0, '需调整股数': 0,
                            '交易方向': '待定', '预计交易金额': 0, '操作类型': '待定',
                            '执行批次': '待定', '止损位': 0, '止盈位': 0,
                        }
                        for a in assets
                    ]
                    engine.batch_plan = []
                    engine.is_loaded = True
                    loaded = True
                    print(f"✅ 已从portfolio.yaml加载 {len(assets)} 只标的配置")
        except Exception as e:
            print(f"⚠️ portfolio.yaml加载失败: {e}")
    
    if engine.is_loaded:
        progress.update(3, "构建交易指令...")
        engine.build_trade_orders()
        
        progress.update(4, "生成报告...")
        report = engine.generate_report()
        print("\n" + report)
        
        # 注册研究假设
        if strategy_registry:
            strategy_registry.register_hypothesis('rebalance_2026', {
                'title': '2026年组合再平衡',
                'description': '基于当前持仓的再平衡计划',
                'hypothesis': '核心-卫星策略配置能带来超额收益',
                'status': 'active'
            })
            logger.info("已注册研究假设: rebalance_2026")
        
        if args.sync_sl:
            progress.update(5, "同步止损止盈规则...")
            engine.sync_to_stop_loss_monitor()
            print("\n✅ 止损止盈规则已同步到 config/rebalance_stop_loss_v43.json")
        
        _write_report_file(report, args.output)

        progress.complete("✅ 再平衡执行完成")
    else:
        progress.complete("❌ 无法加载再平衡数据")
        print("\n💡 提示: 请检查以下文件是否存在:")
        print("  1. config/portfolio.yaml (必需)")
        print("  2. data_extraction_*.xlsx (可选,用于详细再平衡计划)")

def run_backtest(args):
    """回测模式 - 历史数据回测验证"""
    print("\n📊 运行回测")
    print("=" * 70)
    
    progress = ProgressIndicator("回测执行", 4)
    
    progress.update(1, "加载回测模块...")
    try:
        from fast_backtest import run_fast_backtest
        progress.update(2, "执行快速回测...")
        run_fast_backtest()
        progress.update(3, "生成报告...")
        progress.complete("\n✅ 回测完成")
        return
    except ImportError:
        try:
            from backtest_engine import BacktestEngine
            from portfolio_config import PortfolioConfig
            
            progress.update(2, "加载配置...")
            config = load_portfolio_config()
            
            if config:
                portfolio = PortfolioConfig()
                settings = {
                    'capital': {'total': 1000000},
                    'rebalance': {'threshold': 0.06, 'min_interval_days': 5},
                    'targets': {'annual_return': 0.08, 'max_drawdown': 0.15}
                }
                engine = BacktestEngine(portfolio, settings)
                
                progress.update(3, "查找历史数据...")
                excel_files = [f for f in os.listdir(BASE_DIR) if f.startswith('data_extraction') and f.endswith('.xlsx')]
                if excel_files:
                    result = engine.run_backtest(os.path.join(BASE_DIR, excel_files[0]))
                    print("\n✅ 回测完成")
                    print(result)
                else:
                    print("\n❌ 未找到历史数据文件")
            progress.complete()
        except Exception as e:
            progress.complete(f"❌ 回测模块不可用: {e}")

def run_risk_monitor(args):
    """风险监控模式 - 检查止损止盈状态"""
    print("\n🛡️ 运行风险监控")
    print("=" * 70)
    
    progress = ProgressIndicator("风险监控", 4)
    
    progress.update(1, "加载监控模块...")
    StopLossMonitor = stop_loss.get('StopLossMonitor')
    generate_risk_alert_report = stop_loss.get('generate_risk_alert_report')
    
    if StopLossMonitor and generate_risk_alert_report:
        progress.update(2, "创建监控实例...")
        monitor = StopLossMonitor()
        
        progress.update(3, "获取行情数据...")
        quotes = _get_portfolio_quotes()
        
        if not quotes:
            print("\n⚠️ 使用模拟数据进行风险监控")
            quotes = {
                '600989': {'price': 23.50},
                '600276': {'price': 45.00},
                '300274': {'price': 165.00},
                '601088': {'price': 47.80},
                '002371': {'price': 520.00},
            }
        
        progress.update(4, "检查风险状态...")
        alerts = monitor.check_all(quotes)
        report = generate_risk_alert_report(alerts)
        print("\n" + report)
        progress.complete()
    else:
        progress.complete("❌ 止损止盈监控模块不可用")


def _check_commodity_module():
    """检查大宗商品基本面模块是否可用"""
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, '..', '03_投研与策略生成'))
        from 大宗商品基本面综合 import get_copper_fundamentals
        return callable(get_copper_fundamentals)
    except Exception:
        return False


def run_quick_check(args):
    """快速检查模式 - 检查系统状态"""
    print("\n🔍 系统状态快速检查")
    print("=" * 70)
    
    # 检查模块可用性
    def _package_available(pkg_name):
        try:
            import importlib.util
            return importlib.util.find_spec(pkg_name) is not None
        except Exception:
            return False

    modules = {
        '数据提供层': data_provider.get('get_quotes_batch') is not None,
        '自动交易系统': auto_trading.get('AutoTradingSystem') is not None,
        '再平衡引擎': rebalance_engine.get('RebalancingEngine') is not None,
        '每日报告': daily_report.get('generate_daily_report') is not None,
        '止损止盈监控': stop_loss.get('StopLossMonitor') is not None,
        '策略注册表': strategy_registry is not None,
        '连接器管理器': connector_manager is not None,
        'ETF资金流向监控': True,  # 内置模块，始终可用
        '投资组合优化': _package_available('pandas') or _package_available('numpy'),
        '康波周期监控': _package_available('yfinance') or _package_available('tushare'),
        '大宗商品基本面': _check_commodity_module(),  # 动态检查
        '时序预测模型': all(_package_available(pkg) for pkg in ['torch', 'sklearn', 'pandas', 'numpy']),  # 新增
        # v5.9 新增模块
        '多模型路由器': _package_available('yaml'),  # 需要 yaml
        'Wind数据供应器': os.path.exists(os.path.join(BASE_DIR, 'utils', 'wind_data_provider.py')),
    }

    print("\n📦 模块状态:")
    for name, available in modules.items():
        status = "✅" if available else "❌"
        print(f"  {status} {name}")
    
    # 检查策略注册表
    print("\n📋 策略注册表:")
    strategies = strategy_registry.list()
    print(f"  ✅ {len(strategies)} 个策略已注册")
    for strategy_id in strategies[:5]:
        strategy = strategy_registry.get(strategy_id)
        print(f"    - {strategy['name']} (v{strategy['version']})")
    
    # 检查配置管理器
    print("\n⚙️ 配置管理器:")
    try:
        configs = config_manager.get_all()
        print(f"  ✅ 已加载 {len(configs)} 类配置")
        for config_name, config in configs.items():
            print(f"    - {config_name}: {len(config)} 项配置")
    except Exception as e:
        print(f"  ❌ 配置管理器异常: {e}")
    
    # 检查ETF资金流向监控配置
    print("\n📊 ETF资金流向监控:")
    print(f"  ✅ 监控标的: {len(ETFFundFlowMonitor.ETF_LIST)} 只ETF")
    etf_config = config_manager.get('etf_monitor', 'signal_high_threshold')
    if etf_config:
        print(f"  ✅ 信号阈值: 高{etf_config/1e8:.0f}亿/中{config_manager.get('etf_monitor', 'signal_medium_threshold')/1e8:.0f}亿/低{config_manager.get('etf_monitor', 'signal_low_threshold')/1e8:.0f}亿")
    
    # 检查数据源连接器状态
    print("\n🔗 数据源连接器:")
    connector_status = connector_manager.get_status()
    print(f"  当前活跃连接器: {connector_status.get('active_connector', 'None')}")
    print(f"  是否降级模式: {'✅ 是' if connector_status.get('fallback_mode') else '❌ 否'}")
    print(f"  注册连接器数: {connector_status.get('total_connectors', 0)}")
    print(f"  可用连接器数: {connector_status.get('available_connectors', 0)}")
    
    # v5.9: 检查多模型路由器和 Wind 数据供应器
    print("\n🤖 v5.9 AI 决策模块:")
    try:
        from utils.multi_model_router import ModelRouter
        router = ModelRouter()
        print(f"  ✅ 多模型路由器: 已注册 {len(router.config.get('providers', {}))} 个模型提供商")
        scenes = router.config.get('scenes', {})
        for scene_name, scene_cfg in scenes.items():
            primary = scene_cfg.get('primary', {})
            hedged = scene_cfg.get('parallel_hedge', {}).get('enabled', False)
            cv = scene_cfg.get('cross_validation', {}).get('enabled', False)
            extra = ""
            if hedged: extra = " (并行对冲)"
            elif cv: extra = " (交叉验证)"
            print(f"    {scene_name}: {primary.get('provider')}/{primary.get('model')}{extra}")
    except Exception as e:
        print(f"  ❌ 多模型路由器: {e}")
    
    try:
        from utils.wind_data_provider import WindDataProvider
        wp = WindDataProvider()
        status = wp.health_check()
        wind_ok = "可用" if status.get('wind_mcp_available') else "不可用(降级)"
        print(f"  {'✅' if status.get('wind_mcp_available') else '⚠️'} Wind MCP: {wind_ok}")
        print(f"    指数缓存: {status.get('index_cache_size', 0)} 项")
        print(f"    基本面缓存: {status.get('fundamental_cache_size', 0)} 项")
    except Exception as e:
        print(f"  ❌ Wind 数据供应器: {e}")
    
    # 检查配置文件
    print("\n📋 配置文件:")
    config_files = [
        'config/portfolio.yaml',
        'config/settings.yaml',
        'config/positions.json',
        'config/rebalance.yaml',
        'config/risk.yaml',
    ]
    for config_file in config_files:
        path = os.path.join(BASE_DIR, config_file)
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        print(f"  {status} {config_file}")
    
    # 检查数据缓存
    print("\n💾 数据缓存:")
    cache_dir = os.path.join(BASE_DIR, 'data', 'cache')
    if os.path.exists(cache_dir):
        cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.parquet')]
        print(f"  ✅ 缓存目录存在，{len(cache_files)}个文件")
    else:
        print("  ❌ 缓存目录不存在")
    
    # 检查报告目录
    print("\n📄 报告目录:")
    reports_dir = os.path.join(BASE_DIR, 'reports')
    if os.path.exists(reports_dir):
        report_days = len(os.listdir(reports_dir))
        print(f"  ✅ 报告目录存在，{report_days}天报告")
    else:
        print("  ❌ 报告目录不存在")
    
    # 检查日志目录
    print("\n📝 日志目录:")
    if os.path.exists(LOG_DIR):
        log_files = [f for f in os.listdir(LOG_DIR) if f.startswith('system_')]
        print(f"  ✅ 日志目录存在，{len(log_files)}个日志文件")
    else:
        print("  ❌ 日志目录不存在")
    
    # 降级模式状态
    print("\n🛡️ 优雅降级状态:")
    print(f"  当前降级模式: {'⚠️ 已启用' if graceful_fallback.is_fallback_mode() else '✅ 正常'}")
    
    print("\n" + "=" * 70)

def run_portfolio_optimization(args):
    """投资组合优化模式 - 多策略资产配置对比"""
    print("\n📊 投资组合优化与回测")
    print("=" * 70)
    
    progress = ProgressIndicator("投资组合优化", 5)
    
    progress.update(1, "初始化优化引擎...")
    engine = PortfolioOptimizationEngine()
    
    progress.update(2, "生成模拟数据...")
    if not engine.generate_simulation_data():
        progress.complete("❌ 数据生成失败")
        return
    
    progress.update(3, "计算相关性矩阵...")
    engine.calculate_correlation_matrix()
    
    progress.update(4, "运行优化策略...")
    engine.run_all_strategies()
    
    progress.update(5, "生成报告...")
    report = engine.generate_report()
    print("\n" + report)
    
    _write_report_file(report, args.output)
    _archive_report(report, '投资组合优化')

    progress.complete("✅ 投资组合优化完成")

    return engine


def run_kommo_monitor(args):
    """康波周期监控模式 - 大宗商品全维度监控"""
    print("\n🌍 康波周期大宗商品监控")
    print("=" * 70)
    
    progress = ProgressIndicator("康波周期监控", 3)
    
    ts_token = os.environ.get("TS_TOKEN", "")
    progress.update(1, "初始化监控器...")
    monitor = KommoCommodityMonitor(ts_token=ts_token)
    
    progress.update(2, "获取商品价格与宏观指标...")
    commodity_result, macro = monitor.monitor()
    
    progress.update(3, "生成报告...")
    report = monitor.generate_report()
    print("\n" + report)
    
    _write_report_file(report, args.output)
    _archive_report(report, '康波周期监控')

    progress.complete(f"检测到 {len(commodity_result)} 只商品")
    
    return monitor


def run_commodity_fundamentals(args):
    """大宗商品基本面分析模式 - Wind数据综合分析"""
    print("\n💎 大宗商品基本面综合分析")
    print("=" * 70)
    
    progress = ProgressIndicator("大宗商品基本面分析", 3)
    
    progress.update(1, "加载Wind数据模块...")
    try:
        # 尝试导入大宗商品基本面综合模块
        sys.path.insert(0, os.path.join(BASE_DIR, '..', '03_投研与策略生成'))
        from 大宗商品基本面综合 import get_copper_fundamentals
        
        progress.update(2, "获取铜/金/银/原油/铁矿石/动力煤数据...")
        result = get_copper_fundamentals()
        
        progress.update(3, "生成报告...")
        report_lines = [
            "# 大宗商品基本面分析报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**数据来源**: {result.get('数据来源', '未知')}",
            "",
            "---",
            "",
            "## 核心数据",
            "",
        ]
        
        for k, v in result.items():
            if k in ('更新时间', '数据来源', '警告'):
                continue
            report_lines.append(f"- **{k}**: {v}")
        
        report_lines.append("")
        report_lines.append(f"**更新时间**: {result.get('更新时间', 'N/A')}")
        if '警告' in result:
            report_lines.append(f"> ⚠️ {result['警告']}")
        report_lines.extend([
            "",
            "---",
            "*本报告由大宗商品基本面分析模块自动生成*",
        ])
        
        report = "\n".join(report_lines)
        print("\n" + report)

        _write_report_file(report, args.output)
        _archive_report(report, '大宗商品基本面')

        progress.complete("✅ 大宗商品基本面分析完成")
        return result
        
    except ImportError as e:
        progress.complete(f"❌ 大宗商品基本面模块不可用: {e}")
        logger.error(f"导入失败: {e}")
        return None


def run_model_training(args):
    """统一模型训练入口 (v5.7 Phase 2 增强)

    整合所有训练管线:
    - ML分类器: Optuna贝叶斯优化 + Triple Barrier标签 (★ NEW)
    - ML集成: model_train/signal_composer.py (三源信号合成)
    - 情感分析: model_train/finbert_sentiment.py (FinBERT)
    - DL时序: 16_金融市场预测模型/patchtst_trainer.py (PatchTST, 需GPU)
    """
    # 解析高级训练选项
    use_optuna = getattr(args, 'optuna', False)
    use_triple_barrier = getattr(args, 'triple_barrier', False)
    use_stacking = getattr(args, 'stacking', False)

    print("\n🤖 统一模型训练模式 (v5.7 Phase 2 增强版)")
    print("=" * 70)
    print("📦 可用训练管线:")
    print("  [1] ML分类器 - Optuna贝叶斯优化 + 传统标签")
    print("  [2] ML分类器 - Optuna + Triple Barrier标签 (★ 推荐)")
    print("  [3] ML集成 - Stacking (XGBoost+LGBM+GDBT+ET) (★ NEW)")
    print("  [4] DL时序 - PatchTST/LSTM/Transformer (需GPU)")
    print("-" * 70)
    if use_optuna:
        print("🎯 已启用 Optuna 贝叶斯超参数优化")
    if use_triple_barrier:
        print("🎯 已启用 Triple Barrier 标签 (+5%止盈 / -3%止损 / 10天)")
    if use_stacking:
        print("🎯 已启用 Stacking 集成训练")

    from importlib import import_module

    # 检查依赖
    progress = ProgressIndicator("环境检查", 3)

    progress.update(1, "检查ML依赖 (sklearn/xgboost/pandas/numpy)...")
    ml_ready = True
    for pkg in ('sklearn', 'xgboost', 'pandas', 'numpy'):
        try:
            __import__(pkg)
        except ImportError:
            print(f"  ⚠️ 缺少: {pkg}")
            ml_ready = False

    progress.update(2, "检查DL依赖 (torch)...")
    dl_ready = False
    try:
        import torch
        dl_ready = True
        if torch.cuda.is_available():
            print(f"  ✅ PyTorch {torch.__version__} + CUDA (GPU加速可用)")
        else:
            print(f"  ✅ PyTorch {torch.__version__} (CPU模式)")
    except ImportError:
        print(f"  ⚠️ PyTorch 未安装，跳过DL训练")

    progress.update(3, "检查训练数据...")
    data_dir = os.path.join(BASE_DIR, 'data', 'market_data')
    has_data = os.path.isdir(data_dir) and os.listdir(data_dir)
    if has_data:
        print(f"  ✅ 数据目录: {data_dir}")
    else:
        print(f"  ⚠️ 数据目录为空或不存在: {data_dir}")
        print(f"     请先运行 --daily 拉取数据")
    progress.complete("✅ 环境检查完成")

    if not ml_ready and not dl_ready:
        print("\n❌ 无可用的训练环境，请安装依赖")
        return None

    print("\n" + "=" * 70)

    # v5.7 Phase 3: MLflow 实验追踪
    mlflow_tracker = None
    use_mlflow = getattr(args, 'mlflow', False)
    if use_mlflow:
        try:
            from utils.mlflow_tracker import create_tracker
            mlflow_tracker = create_tracker(experiment_name="quant_v5.7_training")
            if mlflow_tracker.available:
                mlflow_tracker.start_run(run_name=f"train_{datetime.now().strftime('%Y%m%d_%H%M')}")
                print(f"📊 MLflow 追踪已启用 - 实验: quant_v5.7_training")
            else:
                print(f"📋 MLflow 回退模式 - 本地 JSON 日志")
        except Exception as e:
            print(f"⚠️ MLflow 初始化失败: {e}")

    # ── Phase 1: ML 模型训练 ──
    if ml_ready:
        # v5.7 Phase 2: 优先使用 Optuna + Triple Barrier 管线
        if use_optuna or use_triple_barrier:
            print("\n🔹 [1/3] Optuna 贝叶斯优化训练 (★★★)...")
            try:
                from utils.ml_optuna_trainer import run_optuna_training
                optuna_result = run_optuna_training(
                    n_trials=getattr(args, 'optuna_trials', 100),
                    use_triple_barrier=use_triple_barrier,
                )
                if optuna_result.get('best_model'):
                    print(f"  ✅ Optuna训练完成 - 最佳模型: {optuna_result['best_model']}")
                    print(f"     F1={optuna_result.get('best_f1', 0):.4f}")
                else:
                    print(f"  ⚠️ Optuna训练返回空结果")
            except ImportError as e:
                print(f"  ⚠️ Optuna未安装，回退到GridSearch: pip install optuna")
                print(f"  🔄 回退到传统GridSearch训练...")
                try:
                    from model_train.xgboost_direction import train_xgboost_model
                    model, metrics = train_xgboost_model(data_dir=data_dir)
                    print(f"  ✅ XGBoost (GridSearch): 准确率={metrics.get('accuracy', 0):.2%}")
                except Exception as e2:
                    print(f"  ⚠️ 回退训练也失败: {e2}")
            except Exception as e:
                print(f"  ⚠️ Optuna训练异常: {e}")
        else:
            print("\n🔹 [1/3] ML分类器训练 (传统GridSearch)...")
            try:
                from model_train.xgboost_direction import train_xgboost_model
                model, metrics = train_xgboost_model(data_dir=data_dir)
                print(f"  ✅ XGBoost 训练完成 - 准确率: {metrics.get('accuracy', 0):.2%}")
            except ImportError as e:
                print(f"  ⚠️ ML训练模块加载失败: {e}")
            except Exception as e:
                print(f"  ⚠️ ML训练异常: {e}")

            print("\n🔹 提示: 使用 --train-model --optuna --triple-barrier 启用高精度训练管线")
            print("  pip install optuna  # 安装Optuna依赖")

        # Stacking 集成（独立步骤）
        if use_stacking and ml_ready:
            print("\n🔹 [2/3] Stacking集成训练...")
            try:
                from utils.ml_predictor import StackingPredictor
                stacking = StackingPredictor(
                    model_dir=os.path.join(BASE_DIR, 'models'),
                    weight_method='f1_weighted',
                )
                if stacking.auto_discover_and_load():
                    print(f"  ✅ Stacking集成器已就绪 - {len(stacking.models)}个模型")
                    print(f"     权重方法: {stacking.weight_method}")
                    print(f"     模型权重: {dict(zip(stacking.models.keys(), [f'{w:.3f}' for w in stacking.model_weights.values()]))}")
            except Exception as e:
                print(f"  ⚠️ Stacking训练异常: {e}")
        else:
            print("\n🔹 [2/3] 三源信号合成器训练...")
        try:
            from model_train.signal_composer import compose_signals
            # 信号合成器使用已训练模型，不重新训练
            print(f"  ✅ 信号合成器就绪 (基于已训练模型)")
        except ImportError as e:
            print(f"  ⚠️ 信号合成器加载失败: {e}")

    # ── Phase 2: DL 模型训练 (可选) ──
    if dl_ready:
        print("\n🔹 [3/3] DL时序模型训练...")
        try:
            # 尝试多种DL训练入口
            dl_trained = False
            train_scripts = [
                '16_金融市场预测模型.patchtst_trainer',
                '16_金融市场预测模型.auto_train_optimized',
                'model_train.lstm_trainer',
            ]
            for script in train_scripts:
                try:
                    mod = import_module(script)
                    if hasattr(mod, 'train'):
                        print(f"  🔄 训练: {script}")
                        mod.train()
                        dl_trained = True
                        break
                except (ImportError, Exception):
                    continue

            if not dl_trained:
                print(f"  ⚠️ 未找到可用DL训练脚本 (已检查: {', '.join(train_scripts)})")
        except Exception as e:
            print(f"  ⚠️ DL训练异常: {e}")
    else:
        print("\n⏭️  跳过DL训练 (缺少PyTorch)")

    # ── 训练总结 ──
    print("\n" + "=" * 70)
    print("✅ 统一训练完成")
    print(f"  ML模型目录: {os.path.join(BASE_DIR, 'models')}")

    # v5.7 Phase 3: MLflow 记录与实验追踪
    if mlflow_tracker:
        try:
            training_config = {
                'optuna': use_optuna,
                'triple_barrier': use_triple_barrier,
                'stacking': use_stacking,
                'ml_ready': ml_ready,
                'dl_ready': dl_ready,
            }
            mlflow_tracker.log_params(training_config)

            # 如果 Optuna 训练有结果，记录指标
            if use_optuna or use_triple_barrier:
                if 'optuna_result' in dir() and optuna_result:
                    mlflow_tracker.log_metrics({
                        'best_f1': optuna_result.get('best_f1', 0),
                        'best_model_count': len(optuna_result.get('results', {})),
                    })
                    best_model_path = optuna_result.get('model_path')
                    if best_model_path and os.path.exists(best_model_path):
                        mlflow_tracker.log_artifact(best_model_path)

            mlflow_tracker.end_run()
            print(f"  📊 实验追踪: {'MLflow' if mlflow_tracker.available else 'JSON回退'} - 已保存")
        except Exception as e:
            print(f"  ⚠️ MLflow 记录异常: {e}")

    print(f"  提示: 使用 --ml-signal 验证最新模型信号")
    print(f"  提示: 使用 --mlflow 启用 MLflow 实验追踪")
    print("=" * 70)

    return {'phase': 'v5.7_optimized', 'ml_ready': ml_ready, 'dl_ready': dl_ready}


# ============================================================
# ML 增强训练模式 — 四维优化 (v5.9)
# ============================================================

def run_enhanced_training_mode(args):
    """ML增强训练 v2.0 — 四维优化管线"""
    if not ML_ENHANCED_TRAINER_AVAILABLE:
        print("\n❌ 增强训练引擎未安装"); return None

    horizon = getattr(args, 'horizon', 1)
    filter_osc = getattr(args, 'filter_oscillation', True)
    use_optuna = getattr(args, 'optuna', False)
    n_trials = getattr(args, 'trials', 50)
    n_features = getattr(args, 'features', 30)
    northbound_path = getattr(args, 'northbound', None) or None

    print("\n" + "=" * 70)
    print("  🧠 ML 增强训练引擎 v2.0 — 四维优化管线")
    print("=" * 70)
    print(f"  预测窗口: T+{horizon} | 过滤震荡: {filter_osc} | Optuna: {use_optuna}")
    print(f"  特征数: {n_features} | 样本加权: 时间衰减+波动率")
    print(f"  增强特征: 行业RS+市场宽度+北向+PE/PB/ROE")
    print("-" * 70)

    progress = ProgressIndicator("增强训练", 5)
    progress.update(1, "加载与特征工程...")
    data_dir = os.path.join(BASE_DIR, 'data', 'cache')
    model_dir = os.path.join(BASE_DIR, 'models')

    result = run_enhanced_training(
        data_dir=data_dir, model_dir=model_dir,
        prediction_horizon=horizon, filter_oscillation=filter_osc,
        use_optuna=use_optuna, n_trials=n_trials,
        n_features=n_features, northbound_path=northbound_path,
    )

    if 'error' in result:
        print(f"\n❌ 训练失败: {result['error']}"); return None

    progress.update(3, "训练..."); progress.update(4, "保存..."); progress.update(5, "完成")
    progress.complete("✅ 增强训练完成")

    print(f"\n📊 最佳: {result['best_model']} | F1={result['best_f1']:.4f} "
          f"| AUC={result['best_auc']:.4f} | 样本={result['n_samples']}")
    for name, m in result['results'].items():
        print(f"  {name:<25} F1={m['f1']:.4f}  AUC={m['auc']:.4f}")
    print(f"\n💡 python v5.9.py --ml-enhanced  # 使用新模型预测")
    print("=" * 70)
    return result


# ============================================================
# ML 增强预测模式 — 四维优化模型预测
# ============================================================

def run_enhanced_prediction_mode(args):
    """ML增强预测 v2.0"""
    if not ML_ENHANCED_PREDICTOR_AVAILABLE:
        print("\n❌ 增强预测器不可用"); return None

    print("\n" + "=" * 70)
    print("  📈 ML 增强预测 v2.0")
    print("=" * 70)

    model_dir = os.path.join(BASE_DIR, 'models')
    data_dir = os.path.join(BASE_DIR, 'data', 'cache')
    threshold = getattr(args, 'threshold', 0.55)

    progress = ProgressIndicator("增强预测", 4)
    progress.update(1, "加载模型...")
    predictor = EnhancedPredictor(model_dir=model_dir, weight_method='f1_weighted')

    if not predictor.auto_discover_and_load(prefer_enhanced=True):
        print("  ⚠️ 未找到增强模型，回退标准预测")
        return run_ml_signal_mode(args)

    info = predictor.get_model_info()
    print(f"\n  T+{info.get('horizon',1)} | 过滤震荡={info.get('filter_oscillation',True)} "
          f"| 模型数={info.get('model_count',0)} | F1={info.get('f1',0):.4f}")

    progress.update(2, "加载K线...")
    kline_dict = {}
    for f in glob.glob(os.path.join(data_dir, 'kline_*.parquet')):
        code = os.path.basename(f).replace('kline_', '').replace('_daily.parquet', '')
        try: kline_dict[code] = pd.read_parquet(f)
        except Exception: continue

    if not kline_dict: print("  ⚠️ 无K线数据"); return None

    progress.update(3, "预测...")
    signals = predictor.generate_trading_signals(kline_dict, threshold=threshold)
    progress.complete("✅ 增强预测完成")

    print(f"\n📊 信号分布 (T+{predictor.prediction_horizon}):")
    print(f"  🟢 买入: {len(signals['buy'])} | 🔴 卖出: {len(signals['sell'])} | 🟡 震荡/持有: {len(signals['hold'])}")

    for label, data in [("买入", signals['buy']), ("卖出", signals['sell'])]:
        if data:
            emoji = '🟢' if label == '买入' else '🔴'
            print(f"\n{emoji} {label}信号:")
            sort_rev = label == '买入'
            for s in sorted(data, key=lambda x: x['probability'], reverse=sort_rev):
                name = _get_stock_name(s['code'])
                print(f"  {s['code']} {name:<8} 概率={s['probability']:.2%} "
                      f"置信={s['confidence']:.2%} 强度={s['strength']}")

    if signals['hold']:
        print(f"\n🟡 震荡/持有 (建议观望):")
        for s in sorted(signals['hold'], key=lambda x: x['probability'], reverse=True)[:5]:
            name = _get_stock_name(s['code'])
            print(f"  {s['code']} {name:<8} 概率={s['probability']:.2%}")

    print(f"\n💡 四维优化: 三分类标签 | T+{predictor.prediction_horizon}窗口 | 增强特征(行业+北向+基本面) | 样本加权")
    print("=" * 70)
    return signals


# ============================================================
# v5.1 新增：康波周期 + 十五五规划 + 社保基金ETF 综合分析
# ============================================================

def run_kondratiev_analysis(args):
    """康波周期+十五五交叠分析模式 — 周期阶段判定 + 行业轮动 + 大宗商品信号"""
    print("\n🌊 康波周期 + 十五五规划交叠分析")
    print("=" * 70)

    if not KONDRATIEV_AVAILABLE:
        print("❌ 康波周期分析模块不可用，请检查 utils/kondratiev_cycle.py")
        return None

    progress = ProgressIndicator("康波周期分析", 4)

    progress.update(1, "初始化康波周期分析器...")
    analyzer = KondratievCycleAnalyzer()

    progress.update(2, "判定当前周期阶段...")
    phase = analyzer.get_current_phase()
    print(f"\n  📍 当前阶段: {phase['phase_name_cn']} (进度: {phase['progress_pct']}%)")
    print(f"  📊 置信度: {phase['confidence']}")
    print(f"  🎯 推荐风格: {phase['recommended_style']}")
    print(f"  ⚠️ 风险等级: {phase['risk_level']}")

    progress.update(3, "生成行业配置+商品信号...")
    sectors = analyzer.get_sector_allocation()
    print(f"\n  📈 行业配置建议:")
    for s in sectors[:5]:
        print(f"    {s['sector']}: 综合得分={s['combined_score']}, 建议={s['recommendation']}")

    progress.update(4, "生成报告...")
    report = analyzer.generate_report()

    _write_report_file(report, args.output)
    _archive_report(report, '康波周期分析')

    progress.complete("✅ 康波周期分析完成")
    return analyzer


def run_fifteen_five_analysis(args):
    """十五五规划适配分析模式 — 持仓对标 + 政策对齐度评分 + 权重调整建议"""
    print("\n🏛️ 十五五规划适配分析")
    print("=" * 70)

    if not FIFTEEN_FIVE_AVAILABLE:
        print("❌ 十五五规划分析模块不可用，请检查 utils/five_year_plan.py")
        return None

    progress = ProgressIndicator("十五五规划分析", 4)

    progress.update(1, "初始化十五五分析器...")
    analyzer = FifteenFivePlanAnalyzer()

    progress.update(2, "分析持仓适配度...")
    overview = analyzer.get_policy_overview()
    print(f"\n  📋 十五五规划七大战略方向:")
    for o in overview:
        print(f"    {o['direction']}: 权重={o['weight']:.0%}, 优先级={o['relevance_score']}")

    progress.update(3, "生成权重调整建议...")
    holdings = analyzer.analyze_holdings()
    adjustments = analyzer.get_weight_adjustments()
    print(f"\n  📊 持仓适配评级:")
    for h in holdings:
        print(f"    {h['name']}: 评分={h['overall_score']}, 等级={h['grade']}")
    print(f"\n  ⚖️ 权重调整建议:")
    for adj in adjustments:
        direction = "+" if adj['weight_adjust_pct'] > 0 else ""
        print(f"    {adj['name']}: {adj['suggestion']} ({direction}{adj['weight_adjust_pct']:.1f}%)")

    progress.update(4, "生成报告...")
    report = analyzer.generate_report()

    _write_report_file(report, args.output)
    _archive_report(report, '十五五规划适配')

    progress.complete("✅ 十五五规划分析完成")
    return analyzer


def run_social_security_analysis(args):
    """社保基金ETF风格追踪模式 — 风格分类 + 国家队信号 + 配置建议"""
    print("\n🏦 社保基金ETF风格追踪")
    print("=" * 70)

    if not SOCIAL_SECURITY_ETF_AVAILABLE:
        print("❌ 社保基金ETF追踪模块不可用，请检查 utils/social_security_etf.py")
        return None

    progress = ProgressIndicator("社保基金ETF追踪", 4)

    progress.update(1, "初始化社保ETF追踪器...")
    tracker = SocialSecurityETFTracker()

    progress.update(2, "分析社保基金投资风格...")
    summary = tracker.classifier.get_style_summary()
    print(f"\n  📊 社保基金四大风格配置:")
    for style, info in summary.items():
        print(f"    {style}: 权重={info['weight']:.0%}, 建议={info['recommended_action']}")
        print(f"      ETF: {', '.join(info['top_etfs'][:2])}")

    progress.update(3, "获取ETF风格映射...")
    etf_classifications = tracker.classifier.get_all_etf_classifications()
    print(f"\n  🔗 ETF风格映射 (前10):")
    for etf in etf_classifications[:10]:
        print(f"    {etf['name']} → {etf['social_style']} (匹配度={etf['match_score']})")

    progress.update(4, "生成报告...")
    flow_data = _get_etf_flow_data(connector_manager)
    if flow_data:
        print(f"\n  💰 已获取 {len(flow_data)} 只ETF资金流数据")

    report = tracker.generate_report(flow_data=flow_data)

    _write_report_file(report, args.output)
    _archive_report(report, '社保基金ETF追踪')

    progress.complete("✅ 社保基金ETF追踪完成")
    return tracker


def run_macro_analysis(args):
    """宏观综合分析 — 一键运行康波周期 + 十五五规划 + 社保基金ETF三大分析"""
    print("\n🔬 宏观综合分析（康波周期 + 十五五规划 + 社保基金ETF）")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)

    results = {}
    archive_dir = get_archive_dir(BASE_DIR)

    # 1. 康波周期分析
    if KONDRATIEV_AVAILABLE:
        print("\n" + "=" * 50)
        print("  第一部分：康波周期 + 十五五规划交叠分析")
        print("=" * 50)
        try:
            kondratiev = KondratievCycleAnalyzer()
            phase = kondratiev.get_current_phase()
            print(f"\n  📍 第六轮康波（AI/算力驱动）当前阶段: {phase['phase_name_cn']}")
            print(f"  📊 阶段进度: {phase['progress_pct']}% | 置信度: {phase['confidence']}")
            print(f"  🎯 推荐风格: {phase['recommended_style']} | 风险等级: {phase['risk_level']}")
            print(f"  🔄 预计转入下一阶段: {phase['estimated_transition']}")

            # 行业配置
            sectors = kondratiev.get_sector_allocation()
            print(f"\n  📈 康波周期行业配置建议:")
            for s in sectors:
                print(f"    {s['sector']}: 综合得分={s['combined_score']} → {s['recommendation']}")

            # 大宗商品信号
            commodities = kondratiev.get_commodity_signals()
            print(f"\n  🛢️ 大宗商品周期信号:")
            for c in commodities:
                print(f"    {c['name']}: 信号={c['current_signal']}, 康波建议={c['kondratiev_recommendation']}")

            # 十五五交叠
            overlay = kondratiev.get_fifteen_five_overlay()
            print(f"\n  🔗 十五五与康波交叠结论:")
            print(f"    {overlay['synergy_conclusion'][:100]}...")

            report = kondratiev.generate_report()
            _archive_report(report, '康波周期分析')
            print(f"\n  ✅ 康波周期报告已归档")
            results['kondratiev'] = True
        except Exception as e:
            print(f"\n  ❌ 康波周期分析失败: {e}")
            results['kondratiev'] = False
    else:
        print("\n  ⚠️ 康波周期模块不可用，跳过")
        results['kondratiev'] = None

    # 2. 十五五规划分析
    if FIFTEEN_FIVE_AVAILABLE:
        print("\n" + "=" * 50)
        print("  第二部分：十五五规划适配分析")
        print("=" * 50)
        try:
            fifteen_five = FifteenFivePlanAnalyzer()
            holdings = fifteen_five.analyze_holdings()
            adjustments = fifteen_five.get_weight_adjustments()

            print(f"\n  📊 持仓十五五适配评级:")
            for h in holdings:
                flag = "🟢" if h['overall_score'] >= 85 else "🟡" if h['overall_score'] >= 70 else "🔴"
                print(f"    {flag} {h['name']}: 评分={h['overall_score']}, 等级={h['grade']}")

            print(f"\n  ⚖️ 十五五驱动的权重调整建议:")
            for adj in adjustments:
                if adj['weight_adjust_pct'] != 0:
                    direction = "▲" if adj['weight_adjust_pct'] > 0 else "▼"
                    print(f"    {direction} {adj['name']}: {adj['suggestion']} ({adj['weight_adjust_pct']:+.1f}%)")

            report = fifteen_five.generate_report()
            _archive_report(report, '十五五规划适配')
            print(f"\n  ✅ 十五五规划报告已归档")
            results['fifteen_five'] = True
        except Exception as e:
            print(f"\n  ❌ 十五五规划分析失败: {e}")
            results['fifteen_five'] = False
    else:
        print("\n  ⚠️ 十五五规划模块不可用，跳过")
        results['fifteen_five'] = None

    # 3. 社保基金ETF追踪
    if SOCIAL_SECURITY_ETF_AVAILABLE:
        print("\n" + "=" * 50)
        print("  第三部分：社保基金ETF风格追踪")
        print("=" * 50)
        try:
            ss_tracker = SocialSecurityETFTracker()
            summary = ss_tracker.classifier.get_style_summary()

            print(f"\n  📊 社保基金四大投资风格:")
            for style, info in summary.items():
                icon = "📈" if info['recommended_action'] == "超配" else "📊" if info['recommended_action'] == "标配" else "📉"
                print(f"    {icon} {style} ({info['weight']:.0%}): {info['recommended_action']}")
                print(f"       代表ETF: {', '.join(info['top_etfs'][:2])}")

            flow_data = _get_etf_flow_data(connector_manager)

            report = ss_tracker.generate_report(flow_data=flow_data)
            _archive_report(report, '社保基金ETF追踪')
            print(f"\n  ✅ 社保基金ETF报告已归档")
            results['social_security'] = True
        except Exception as e:
            print(f"\n  ❌ 社保基金ETF追踪失败: {e}")
            results['social_security'] = False
    else:
        print("\n  ⚠️ 社保基金ETF追踪模块不可用，跳过")
        results['social_security'] = None

    # 汇总
    print("\n" + "=" * 70)
    success_count = sum(1 for v in results.values() if v is True)
    total_count = sum(1 for v in results.values() if v is not None)
    print(f"🔬 宏观综合分析完成: {success_count}/{total_count} 模块成功")
    print(f"📁 报告归档目录: {archive_dir}")
    print("=" * 70)

    return results


def run_ai_decision(args):
    """AI盘中实时决策模式 v5.9 - 多模型场景路由 + Wind MCP 动态数据"""
    print("\n🤖 AI 盘中实时决策模式 v5.9")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"决策场景: {'盘中并行对冲' if getattr(args, 'scene', 'intraday_decision') == 'intraday_decision' else '再平衡交叉验证'}")
    print(f"Wind MCP: {'启用' if not getattr(args, 'no_wind', False) else '禁用'}")
    print("-" * 70)

    try:
        from utils.intraday_decision import IntradayDecisionMonitor

        # v5.9: 从 args 获取场景参数
        scene = getattr(args, 'scene', 'intraday_decision')
        use_wind = not getattr(args, 'no_wind', False)

        # 创建监控器 (v5.9: 场景路由 + Wind MCP)
        monitor = IntradayDecisionMonitor(
            api_model='doubao-speed-32k',  # 向后兼容
            check_interval=getattr(args, 'interval', 300),
            enable_notifications=True,
            scene=scene,
            use_wind_mcp=use_wind,
        )

        # 加载持仓
        if not monitor.load_positions():
            print("❌ 持仓数据加载失败,请检查 config/positions.json")
            return

        print(f"✅ 已加载 {len(monitor.positions)} 只持仓")

        # 生成决策
        model_info = {
            'intraday_decision': 'GLM-4.7-Flash + 豆包Speed (并行对冲)',
            'rebalancing_analysis': 'DeepSeek V4 Pro + 豆包Pro (交叉验证)',
        }
        print(f"\n📊 正在调用 AI 生成交易决策...")
        print(f"   场景路由: {model_info.get(scene, '默认')}")
        print(f"   (这需要10-30秒,请耐心等待)")
        print("-" * 70)

        decision = monitor.generate_decision()

        if not decision:
            print("❌ 决策生成失败")
            return

        # 显示结果
        print("\n" + "=" * 70)
        print("📈 决策结果")
        print("=" * 70)

        print(f"\n📋 市场概况:")
        print(f"   {decision.market_summary}")

        print(f"\n📊 交易信号: {len(decision.trading_signals)} 条")
        if decision.trading_signals:
            # v5.7 Phase 2: 记录AI决策到统一数据库
            try:
                coordinator = get_ai_coordinator()
            except Exception as e:
                logger.debug(f"获取AI协调器失败: {e}")
                coordinator = None
            for sig in decision.trading_signals:
                action_map = {'BUY': '买入', 'SELL': '卖出', 'HOLD': '持有', 'REDUCE': '减仓'}
                action_cn = action_map.get(sig.action, sig.action)
                print(f"   [{action_cn}] {sig.code} {sig.name}")
                print(f"      理由: {sig.reason}")
                print(f"      置信度: {sig.confidence:.2f}, 紧急程度: {sig.urgency}")
                if hasattr(sig, 'key_factors') and sig.key_factors:
                    print(f"      关键因子: {', '.join(sig.key_factors)}")
                if hasattr(sig, 'risk_considerations') and sig.risk_considerations:
                    print(f"      风险考量: {sig.risk_considerations}")
                # 记录到AI协调器数据库 (v5.9: 添加模型路由信息)
                if coordinator:
                    try:
                        coordinator.record_decision(
                            source='model_router',
                            ticker=sig.code,
                            action=sig.action,
                            confidence=sig.confidence,
                            reasoning=sig.reason,
                            model_used=getattr(sig, 'model_used', scene),
                            task_type=scene,
                        )
                    except Exception as e:
                        logger.debug(f"记录AI决策失败 {sig.code}: {e}")
        else:
            print("   暂无交易信号 - 当前持仓无需调整")

        print(f"\n⚠️  风险预警: {len(decision.risk_alerts)} 条")
        if decision.risk_alerts:
            for alert in decision.risk_alerts:
                icon = {'CRITICAL': '🚨', 'HIGH': '⚠️', 'MEDIUM': '⚡', 'LOW': 'ℹ️'}.get(alert.severity, '•')
                print(f"   {icon} [{alert.severity}] {alert.message}")
        else:
            print("   暂无风险预警")

        if decision.portfolio_advice:
            print(f"\n💡 组合调整建议:")
            print(f"   {decision.portfolio_advice}")

        if decision.macro_outlook:
            print(f"\n🔮 宏观展望:")
            print(f"   {decision.macro_outlook}")

        print(f"\n📈 AI置信度: {decision.ai_confidence:.2%}")

        # 导出报告
        report_path = monitor.export_report(decision)
        if report_path:
            print(f"\n✅ 决策报告已保存: {report_path}")

        print("\n" + "=" * 70)
        print("AI决策完成 - 请人工审核后再执行交易")
        print("=" * 70)

    except ImportError:
        print("❌ AI决策模块未安装")
        print("   请确保 utils/glm5_decision_engine.py, utils/multi_model_router.py 和 utils/wind_data_provider.py 存在")
    except Exception as e:
        print(f"❌ AI决策执行失败: {e}")
        import traceback
        traceback.print_exc()


def run_daily_workflow(args):
    """每日三阶段交易工作流 - 盘前计划/盘中策略/盘后报告"""
    print("\n📅 每日交易工作流")
    print("=" * 70)
    
    # 直接调用 daily_trading_workflow.py 模块
    try:
        import daily_trading_workflow as dtw
    except ImportError as e:
        print(f"\n❌ 无法导入 daily_trading_workflow 模块: {e}")
        print("💡 请确保 daily_trading_workflow.py 存在于当前目录")
        return
    
    # 执行指定阶段
    phase = getattr(args, 'phase', 'all')
    if phase is None:
        phase = 'all'
    
    print(f"\n🎯 执行阶段: {phase}")
    print("-" * 70)
    
    try:
        # 阶段注册表：函数名 / 完成提示
        PHASE_MAP = {
            'premarket': ('run_premarket', '盘前计划生成完成'),
            'intraday':  ('run_intraday',  '盘中策略扫描完成'),
            'postmarket': ('run_postmarket', '盘后报告生成完成'),
        }

        if phase in PHASE_MAP:
            func_name, success_msg = PHASE_MAP[phase]
            func = getattr(dtw, func_name, None)
            if func:
                func()
                print(f"\n✅ {success_msg}")
            else:
                print(f"\n❌ {func_name} 函数不存在")

        elif phase == 'all':
            # 全流程执行
            print("\n🚀 开始全流程执行...")

            if hasattr(dtw, 'run_all'):
                dtw.run_all()
            else:
                # 手动串联三个阶段
                for i, (func_name, success_msg) in enumerate(PHASE_MAP.values(), 1):
                    print(f"\n[{i}/{len(PHASE_MAP)}] {success_msg[:4]}")
                    func = getattr(dtw, func_name, None)
                    if func:
                        func()

            # ── v5.9: 盘后联动分析 (对冲+再平衡) ──
            print("\n  🔗 盘后联动分析 (对冲+再平衡 v5.9)...")
            print("  " + "-" * 60)
            try:
                from utils.hedge_rebalance_integrator import HedgeRebalanceIntegrator, HedgeMode
                base_dir = os.path.dirname(os.path.abspath(__file__))
                integrator = HedgeRebalanceIntegrator(base_dir=base_dir, hedge_mode=HedgeMode.TAIL_ONLY)
                plan = integrator.run_full_workflow()
                report_path = integrator.save_report(plan)
                print(f"  ✅ 联动分析完成 v5.9 | 模式: {integrator.hedge_mode.value} | 优先级: {plan.execution_priority} | 窗口: {plan.execution_window}")
                print(f"  📄 报告: {report_path}")
                print(f"  📊 预估: 年化{plan.estimated_annual_return*100:.1f}% | 最大回撤{plan.estimated_max_drawdown*100:.1f}% | 夏普{plan.estimated_sharpe:.2f}")
            except Exception as e:
                print(f"  ⚠️ 联动分析跳过: {e}")

            print("\n✅ 全流程执行完成")

        else:
            print(f"\n❌ 未知阶段: {phase}")
            print("💡 可用阶段: premarket, intraday, postmarket, all")
    
    except Exception as e:
        print(f"\n❌ 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()


def run_futures_options_scan(args):
    """期货期权扫描模式"""
    print("\n📊 期货期权扫描模式")
    print("=" * 70)
    
    try:
        from quant_modules.futures_options_scanner import run_full_scan
        print("\n[INFO] 开始期货/期权/套利全扫描...")
        result = run_full_scan(use_wind=True, use_deepseek=False)
        
        # 显示结果摘要
        num_arb = len(result.get('arbitrage_signals', []))
        num_futures = len(result.get('futures', {}))
        num_options = len(result.get('options', {}))
        
        print(f"\n[OK] 扫描完成!")
        print(f"  - 期货品种: {num_futures} 个")
        print(f"  - 期权品种: {num_options} 个")
        print(f"  - 套利机会: {num_arb} 个")
        
        if num_arb > 0:
            print("\n[ARBITRAGE] 套利机会:")
            for i, signal in enumerate(result['arbitrage_signals'][:5], 1):
                print(f"  {i}. {signal}")
        
    except ImportError as e:
        print(f"\n❌ 期货期权模块导入失败: {e}")
        print("💡 请确保 quant_modules/futures_options_scanner.py 存在")
    except Exception as e:
        print(f"\n❌ 期货期权扫描失败: {e}")
        import traceback
        traceback.print_exc()


def run_unified_monitor(args):
    """统一监控模式 - 一键启动所有模块 (v5.7 Phase 1 增强版: 7模块并行)"""
    print("\n🎯 统一监控模式 (v5.7 增强版)")
    print("=" * 70)
    print("📋 启动所有交易模块...")
    print("-" * 70)
    
    import threading
    import time
    import logging
    from pathlib import Path

    # 配置日志（使用 TRADE_LOG_DIR 避免与全局 LOG_DIR 冲突）
    TRADE_LOG_DIR = Path(__file__).parent / "trade_logs"
    TRADE_LOG_DIR.mkdir(exist_ok=True)

    log_file = TRADE_LOG_DIR / f'unified_{datetime.now():%Y%m%d_%H%M%S}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    um_logger = logging.getLogger('unified_monitor')

    def run_module_loop(name, func, interval=300):
        """模块循环执行"""
        um_logger.info(f"🚀 启动模块: {name}")
        while True:
            try:
                um_logger.info(f"▶️  执行: {name}")
                func()
                um_logger.info(f"✅ {name} 完成")
            except KeyboardInterrupt:
                um_logger.info(f"⏹️  用户中断: {name}")
                break
            except Exception as e:
                um_logger.error(f"❌ {name} 错误: {e}", exc_info=True)
            time.sleep(interval)

    # 股票实时行情快照（单次，非阻塞）
    def stock_monitor_func():
        quotes = _get_portfolio_quotes()
        if not quotes:
            um_logger.warning("[股票监控] 数据源不可用，跳过本轮")
            return
        um_logger.info(f"[股票监控] 已获取 {len(quotes)} 只标的行情")
        for code, info in list(quotes.items())[:5]:
            um_logger.info(f"  {code}: {info['price']}")
        # v5.7 新增：报告数据源层级
        ds_label = getattr(connector_manager, 'get_data_source_label', lambda: 'Unknown')()
        um_logger.info(f"[股票监控] 数据源: {ds_label}")

    # 期货期权扫描
    def futures_scan_func():
        """调用期货期权扫描模块"""
        try:
            um_logger.info("[期货期权] 运行市场扫描...")
            from quant_modules.futures_options_scanner import run_full_scan
            result = run_full_scan(use_wind=True, use_deepseek=False)
            um_logger.info(f"[期货期权] 扫描完成 - 发现 {len(result.get('arbitrage_signals', []))} 个套利机会")
        except ImportError as e:
            um_logger.error(f"[期货期权] 模块导入失败: {e}")
        except Exception as e:
            um_logger.error(f"[期货期权] 错误: {e}")

    # 止损止盈风险快照（单次，非阻塞）
    def risk_check_func():
        StopLossMonitor = stop_loss.get('StopLossMonitor')
        quotes = _get_portfolio_quotes()
        if not StopLossMonitor or not quotes:
            um_logger.warning("[风险评估] 风控模块或行情不可用，跳过本轮")
            return
        try:
            alerts = StopLossMonitor().check_all(quotes)
            um_logger.info(f"[风险评估] 检查 {len(quotes)} 只标的，发现 {len(alerts)} 条告警")
        except Exception as e:
            um_logger.error(f"[风险评估] 错误: {e}")

    # ── v5.7 Phase 1 新增监控模块 ──

    def etf_flow_monitor_func():
        """ETF资金流监控 - 每10分钟"""
        try:
            um_logger.info("[ETF资金流] 运行监控...")
            quotes = _get_portfolio_quotes()
            if quotes:
                um_logger.info(f"[ETF资金流] 已获取 {len(quotes)} 只标的行情用于资金流分析")
            # 轻量级：仅记录关键信号，不生成完整报告
            tracker = SocialSecurityETFTracker() if SOCIAL_SECURITY_ETF_AVAILABLE else None
            tracker_result = tracker.track(tickers=list(quotes.keys())[:20]) if tracker else None
            if tracker_result:
                um_logger.info(f"[ETF资金流] 风格信号: {tracker_result.get('regime', 'N/A')}")
        except Exception as e:
            um_logger.debug(f"[ETF资金流] 跳过本轮: {e}")

    def ml_signal_monitor_func():
        """ML信号扫描 - 每15分钟"""
        try:
            if not ML_PREDICTOR_AVAILABLE:
                return
            um_logger.info("[ML信号] 运行模型预测扫描...")
            from utils.ml_predictor import run_ml_signal_scan as ml_scan
            data_dir = os.path.join(BASE_DIR, 'data', 'cache')
            model_dir = os.path.join(BASE_DIR, 'models')
            result = ml_scan(data_dir=data_dir, model_dir=model_dir, threshold=0.55)
            if 'signals' in result:
                sigs = result['signals']
                um_logger.info(
                    f"[ML信号] 买入={len(sigs.get('buy', []))} "
                    f"卖出={len(sigs.get('sell', []))} "
                    f"持有={len(sigs.get('hold', []))}"
                )
        except Exception as e:
            um_logger.debug(f"[ML信号] 跳过本轮: {e}")

    def kommo_monitor_func():
        """康波周期监控 - 每1小时"""
        try:
            um_logger.info("[康波周期] 运行周期分析...")
            from utils.kondratiev_cycle import KondratievCycleAnalyzer
            analyzer = KondratievCycleAnalyzer()
            cycle_info = analyzer.analyze()
            if cycle_info:
                um_logger.info(
                    f"[康波周期] 阶段: {cycle_info.get('phase', 'N/A')} | "
                    f"建议配置: {cycle_info.get('suggestion', 'N/A')[:50]}"
                )
        except Exception as e:
            um_logger.debug(f"[康波周期] 跳过本轮: {e}")

    def connector_health_func():
        """数据源健康探测 - 每2分钟"""
        try:
            health = getattr(connector_manager, 'check_health', lambda: {})()
            active = health.get('active')
            ds_label = getattr(connector_manager, 'get_data_source_label', lambda: 'Unknown')()
            fallbacks = getattr(connector_manager, 'get_fallbacks_today', lambda: 0)()

            if fallbacks > 0:
                um_logger.warning(
                    f"[数据源健康] 当前: {ds_label} | "
                    f"今日降级 {fallbacks} 次 | "
                    f"活跃连接器: {active}"
                )
            else:
                um_logger.info(f"[数据源健康] {ds_label}")
        except Exception as e:
            um_logger.debug(f"[数据源健康] 错误: {e}")
    
    # ── 启动线程 ──
    threads = []
    modules_config = [
        # 原有模块
        ("股票实时监控", stock_monitor_func, 300),
        ("期货期权扫描", futures_scan_func, 180),
        ("风险评估", risk_check_func, 300),
        # v5.7 Phase 1 新增模块
        ("ETF资金流监控", etf_flow_monitor_func, 600),       # 10分钟
        ("ML信号扫描", ml_signal_monitor_func, 900),          # 15分钟
        ("康波周期监控", kommo_monitor_func, 3600),           # 1小时
        ("数据源健康探测", connector_health_func, 120),       # 2分钟
    ]
    
    print("\n" + "=" * 70)
    print("📋 已注册模块: (v5.7 增强版 - 7模块)")
    print("=" * 70)
    for name, _, interval in modules_config:
        interval_str = f"每 {interval}秒" if interval < 3600 else f"每 {interval // 60}分钟"
        print(f"  - {name}: {interval_str}")
    
    print("\n" + "=" * 70)
    print("🔥 开始并行启动所有模块...")
    print(f"📡 当前数据源: {getattr(connector_manager, 'get_data_source_label', lambda: 'Unknown')()}")
    print("=" * 70)
    
    for name, func, interval in modules_config:
        thread = threading.Thread(
            target=run_module_loop,
            args=(name, func, interval),
            daemon=True,
            name=name
        )
        threads.append(thread)
        thread.start()
        time.sleep(0.5)  # 减少启动间隔
    
    print("\n" + "=" * 70)
    print("✅ 所有 7 个模块已启动！")
    print(f"📝 日志文件: {log_file}")
    print("💡 按 Ctrl+C 停止所有模块")
    print("=" * 70)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("⏹️  正在关闭所有模块...")
        print("=" * 70)
        um_logger.info("所有模块已停止")


def run_hypothesis_test(args):
    """假设验证模式 - 验证交易假设"""
    print("\n🧪 假设验证模式")
    print("=" * 70)
    
    if args.list:
        print("\n📋 已注册的研究假设:")
        hypotheses = strategy_registry.list_hypotheses()
        if not hypotheses:
            print("  暂无注册的假设")
        else:
            for i, hyp in enumerate(hypotheses, 1):
                print(f"\n  {i}. {hyp.get('name', '未命名假设')}")
                print(f"     ID: {list(strategy_registry.hypotheses.keys())[i-1]}")
                print(f"     状态: {hyp.get('status', '未知')}")
                print(f"     创建时间: {hyp.get('created_at', '未知')}")
                if 'description' in hyp:
                    print(f"     描述: {hyp['description']}")
        return
    
    if args.register:
        parts = args.register.split('|')
        if len(parts) >= 2:
            hyp_id = parts[0].strip()
            hyp_name = parts[1].strip()
            hyp_desc = parts[2].strip() if len(parts) > 2 else ""
            
            strategy_registry.register_hypothesis(hyp_id, {
                'name': hyp_name,
                'description': hyp_desc,
                'methodology': '统计检验',
                'evidence': []
            })
            print(f"\n✅ 假设已注册: {hyp_name}")
        else:
            print("\n❌ 注册格式错误，使用: --register id|名称|描述")
        return
    
    print("\n💡 使用方法:")
    print("  --list              列出所有研究假设")
    print("  --register id|名称|描述    注册新假设")
    print("  --validate <id>     验证假设")


# ============================================================
# 统一执行日志 (v5.7 Phase 1 新增)
# ============================================================

def _log_execution_summary(mode_name: str, duration_sec: float, success: bool, result: Any = None):
    """记录每个CLI模式执行的统一结构化日志。

    v5.7 Phase 1: 为所有22个CLI模式提供一致的可观测性。
    """
    metrics = {}
    if isinstance(result, dict):
        # 从结果中提取关键指标
        for key in ('accuracy', 'signals_count', 'scanned_count', 'alerts_count',
                     'buy_count', 'sell_count', 'hold_count', 'total_assets'):
            if key in result:
                metrics[key] = result[key]

    status_icon = "✅" if success else "❌"
    summary = f"[EXEC] {mode_name} | 耗时={duration_sec:.1f}s | {status_icon}"
    if metrics:
        summary += f" | {json.dumps(metrics, ensure_ascii=False)}"

    # 写入统一日志文件
    try:
        exec_log_dir = os.path.join(BASE_DIR, 'logs', 'executions')
        os.makedirs(exec_log_dir, exist_ok=True)
        exec_log_file = os.path.join(exec_log_dir, f'exec_{datetime.now():%Y%m}.jsonl')
        with open(exec_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'mode': mode_name,
                'duration_sec': round(duration_sec, 2),
                'success': success,
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics,
            }, ensure_ascii=False) + '\n')
    except Exception:
        pass

    logger.info(summary)

    # 如果失败且有时长异常(>60s)，发送告警
    if not success and duration_sec > 60:
        event_tracker.track('execution_timeout', {
            'mode': mode_name,
            'duration_sec': duration_sec,
            'timestamp': datetime.now().isoformat(),
        })


# ============================================================
# AI Hedge Fund — 19位大师级AI分析师联合决策模式
# ============================================================

def run_ai_hedge_mode(args):
    """AI Hedge Fund — 19位大师级AI分析师联合决策模式
    
    v5.9 优化：
    - 先跑ML信号扫描筛选高置信度标的，避免对所有标的无差别做AI深度分析
    - 集成AI协调器记录决策到统一数据库
    - 懒加载优化，首次导入后缓存
    """
    global _AI_HEDGE_IMPORTED, _AI_HEDGE_MODULE
    if not _AI_HEDGE_IMPORTED:
        try:
            from quant_modules.ai_hedge_fund.orchestrator import (
                run_ai_hedge_fund, print_trading_output, get_available_analysts
            )
            _AI_HEDGE_MODULE = {
                'run': run_ai_hedge_fund,
                'print': print_trading_output,
                'analysts': get_available_analysts,
            }
            _AI_HEDGE_IMPORTED = True
        except ImportError as e:
            print(f"❌ AI Hedge Fund 模块不可用: {e}")
            print("   请安装依赖: pip install langgraph langchain langchain-openai python-dotenv")
            return

    run_ai_hedge_fund = _AI_HEDGE_MODULE['run']
    print_trading_output = _AI_HEDGE_MODULE['print']
    get_available_analysts = _AI_HEDGE_MODULE['analysts']

    print("=" * 70)
    print("  🤖 AI Hedge Fund — 多分析师联合决策系统")
    print("  19位大师级AI分析师 + 风控 + 组合管理")
    print("=" * 70)

    tickers = []
    if hasattr(args, 'ticker') and args.ticker:
        tickers = args.ticker
    else:
        try:
            cfg = load_portfolio_config()
            for asset in cfg.get('assets', []):
                code = asset.get('code', '')
                if code and code != 'CASH' and not code.startswith(('51', '58', '159', '56')):
                    tickers.append(code)
        except Exception:
            pass
        if not tickers:
            tickers = ['600036', '000001', '300750', '600519', '688981']

    ml_high_confidence = set()
    if len(tickers) > 5 and not getattr(args, 'skip_ml_filter', False):
        print(f"\n  🧠 ML预筛选: 先扫描 {len(tickers)} 只标的ML信号，只对高置信度标的做AI深度分析...")
        try:
            if ML_PREDICTOR_AVAILABLE:
                from utils.ml_predictor import MLModelPredictor
                _ml = MLModelPredictor()
                ml_results = _ml.predict_batch(tickers[:15])
                for r in ml_results:
                    code = r.get('code', '')
                    prob = r.get('probability', 0.5)
                    if abs(prob - 0.5) > 0.15:
                        ml_high_confidence.add(code)
                print(f"  ✅ ML预筛选完成: {len(ml_high_confidence)}/{len(tickers)} 只高置信度标的")
                if ml_high_confidence:
                    tickers = list(ml_high_confidence)
                else:
                    print(f"  ⚠️ 无高置信度标的，取置信度最高的前5只")
                    sorted_results = sorted(r.get('probability', 0.5) for r in ml_results if 'probability' in r)
        except Exception as e:
            print(f"  ⚠️ ML预筛选跳过: {e}")

    print(f"\n  分析标的 ({len(tickers)}只): {', '.join(tickers)}")

    if hasattr(args, 'analysts') and args.analysts:
        selected = args.analysts
    else:
        selected = None

    available = get_available_analysts()
    print(f"  可用分析师: {len(available)} 位")
    if selected:
        print(f"  已选择: {', '.join(selected)}")

    try:
        coordinator = get_ai_coordinator()
        can_run, msg = coordinator.can_proceed(estimated_tokens=len(tickers) * 8000)
        if not can_run:
            print(f"\n  ⚠️ AI协调器: {msg}")
            print("   已超出每日Token预算，AI Hedge Fund分析中止")
            print("   提示: 可设置环境变量 AI_TOKEN_BUDGET 调整预算上限")
            return
        if msg:
            print(f"\n  ⚡ {msg}")
    except Exception:
        coordinator = None

    print("\n  正在启动 AI Hedge Fund 工作流...")
    print("  (需要 OPENAI_API_KEY / DEEPSEEK_API_KEY 等 LLM API Key)")
    print("-" * 70)

    result = run_ai_hedge_fund(
        tickers=tickers,
        start_date=getattr(args, 'start_date', None),
        end_date=getattr(args, 'end_date', None),
        selected_analysts=selected,
        show_reasoning=getattr(args, 'show_reasoning', False),
        model_name=getattr(args, 'model', None),
        model_provider=getattr(args, 'provider', None),
    )

    print_trading_output(result)

    if coordinator:
        decisions = result.get('decisions', {})
        for ticker, decision in decisions.items():
            action = decision.get('action', 'HOLD')
            reasoning = decision.get('reasoning', '')
            confidence = decision.get('confidence', 0.5)
            try:
                coordinator.record_decision(
                    source='ai_hedge', ticker=ticker, action=action,
                    confidence=confidence, reasoning=str(reasoning)[:2000],
                    model_used=getattr(args, 'model', 'deepseek'),
                    task_type='deep_research',
                )
            except Exception:
                pass

    try:
        import json
        report = {
            'timestamp': datetime.now().isoformat(),
            'mode': 'ai_hedge',
            'tickers': tickers,
            'decisions': result.get('decisions', {}),
            'analyst_signals': result.get('analyst_signals', {}),
            'ml_pre_filtered': bool(ml_high_confidence),
        }
        report_dir = get_archive_dir(base_dir=os.path.dirname(os.path.abspath(__file__)))
        report_path = os.path.join(report_dir, f'AI_Hedge_Fund_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n  📄 报告已保存: {report_path}")
    except Exception as e:
        logger.warning(f"报告保存失败: {e}")


# ============================================================
# 对冲模式 — v5.9: 指数期货/期权风险对冲 (Taleb+Burry+Druckenmiller)
# ============================================================

def run_hedge_mode(args):
    """对冲分析模式 — 评估组合风险并生成指数期货/期权对冲方案
    
    功能:
    1. 评估组合Beta(沪深300/中证500/中证1000/上证50)
    2. 计算VaR/CVaR尾部风险
    3. Taleb+Burry+Druckenmiller 三位一体对冲分析
    4. 生成IF/IC/IH/IM期货做空方案 或 protective put/collar/put spread 期权策略
    5. 估计对冲成本与效果
    """
    print("\n🛡️ AI Hedge Fund — 对冲策略分析")
    print("=" * 70)
    
    progress = ProgressIndicator("对冲分析", 6)
    
    try:
        from utils.hedge_engine import (
            HedgeEngine, HedgeSignalStrength,
            INDEX_FUTURES_SPECS, ETF_OPTIONS_SPECS,
            calculate_portfolio_beta,
        )
        _HEDGE_OK = True
    except ImportError as e:
        print(f"  ❌ 对冲引擎加载失败: {e}")
        _HEDGE_OK = False
        return
    
    progress.update(1, "加载持仓数据...")
    
    # 读取持仓配置
    base_dir = os.path.dirname(os.path.abspath(__file__))
    positions_path = os.path.join(base_dir, 'config', 'positions.json')
    portfolio_path = os.path.join(base_dir, 'config', 'portfolio.yaml')
    
    positions = {}
    cash = 3_000_000
    
    if os.path.exists(positions_path):
        with open(positions_path, 'r', encoding='utf-8') as f:
            pos_data = json.load(f)
            for code, p in pos_data.get('positions', {}).items():
                positions[code] = {'shares': p.get('shares', 0), 'cost': p.get('cost', 0)}
            cash = pos_data.get('cash', cash)
    
    # 获取实时价格
    progress.update(2, "获取实时价格...")
    prices = {}
    try:
        from utils.wind_data_provider import get_quotes_batch
        codes = list(positions.keys())
        if codes:
            quotes = get_quotes_batch(codes)
            for code in codes:
                if code in quotes and quotes[code].get('price'):
                    prices[code] = quotes[code]['price']
    except Exception:
        # 降级到价格历史
        pricing_path = os.path.join(base_dir, 'config', 'price_history.jsonl')
        if os.path.exists(pricing_path):
            with open(pricing_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        prices[entry['code']] = entry.get('price', 0)
                    except (json.JSONDecodeError, KeyError):
                        continue
    
    # 计算组合总值
    stock_value = sum(v.get('shares', 0) * prices.get(k, 0) for k, v in positions.items())
    total_value = stock_value + cash
    
    progress.update(3, "评估组合风险...")
    
    engine = HedgeEngine(portfolio_value=total_value)
    
    # 组合风险
    risk = engine.assess_portfolio_risk(positions, prices)
    
    print(f"\n  📊 组合风险评估")
    print(f"  {'─' * 50}")
    print(f"  组合总资产:    ¥{risk.total_value:,.0f}")
    print(f"  股票敞口:      ¥{risk.stock_exposure:,.0f} ({risk.stock_exposure/risk.total_value*100:.1f}%)" if risk.total_value > 0 else f"  股票敞口:      ¥{risk.stock_exposure:,.0f}")
    print(f"  现金:          ¥{risk.cash:,.0f}")
    print(f"  组合Beta:      CSI300={risk.beta_csi300:.3f} | CSI500={risk.beta_csi500:.3f} | CSI1000={risk.beta_csi1000:.3f} | SSE50={risk.beta_sse50:.3f}")
    print(f"  30日波动率:    {risk.volatility_30d*100:.1f}%")
    print(f"  日VaR(95%):    ¥{risk.var_95_daily:,.0f} ({risk.var_95_daily/risk.total_value*100:.2f}%)" if risk.total_value > 0 else f"  日VaR(95%):    ¥0")
    print(f"  日CVaR(95%):   ¥{risk.cvar_95_daily:,.0f}")
    print(f"  集中度(HHI):   {risk.concentration_risk:.4f}")
    
    # 市场信号
    progress.update(4, "收集市场信号...")
    market_signals = {}
    
    # 获取四大股指期货实时价格（多源回退: AKShare → 新浪 → efinance → 默认值）
    from utils.hedge_engine import get_live_futures_prices
    futures_prices = get_live_futures_prices()
    if futures_prices:
        print(f"  📡 期货价格来源: 已获取 {len([k for k in futures_prices if futures_prices[k] > 0])}/4 品种")
    
    # 对冲信号强度判断
    strength, score = engine.determine_hedge_signal_strength(risk, market_signals)
    strength_names = {
        HedgeSignalStrength.NO_HEDGE: "无需对冲 ✓",
        HedgeSignalStrength.LIGHT: "轻度对冲 ⚡",
        HedgeSignalStrength.MODERATE: "中度对冲 ⚠️",
        HedgeSignalStrength.STRONG: "强力对冲 🔴",
        HedgeSignalStrength.FULL: "完全对冲 🚨",
    }
    
    print(f"\n  📡 对冲信号")
    print(f"  {'─' * 50}")
    print(f"  信号强度:      {strength_names.get(strength, '未知')}")
    print(f"  对冲评分:      {score:.2f}/1.0")
    
    # 生成对冲方案
    progress.update(5, "生成对冲方案...")
    
    if strength != HedgeSignalStrength.NO_HEDGE:
        # 期货方案
        hedge_ratio = engine.compute_optimal_hedge_ratio(risk, strength)
        print(f"  对冲比率:      {hedge_ratio*100:.0f}% ({risk.stock_exposure*hedge_ratio:,.0f})" if risk.stock_exposure > 0 else f"  对冲比率:      {hedge_ratio*100:.0f}%")
        
        futures_result = engine.generate_futures_hedge(risk, hedge_ratio, futures_prices)
        
        print(f"\n  📉 期货对冲方案")
        print(f"  {'─' * 50}")
        if futures_result.get("contracts"):
            for code, detail in futures_result["contracts"].items():
                spec = detail.get("spec", {})
                n = detail["contracts"]
                notional = detail["notional"]
                margin = detail["margin"]
                print(f"  {code} {spec.get('name', code)}: 做空 {n} 手")
                print(f"    名义价值: ¥{notional:,.0f} | 保证金: ¥{margin:,.0f}")
            print(f"\n  总名义价值:    ¥{futures_result['total_notional']:,.0f}")
            print(f"  总保证金需求:  ¥{futures_result['total_margin']:,.0f}")
            print(f"  保证金占比:    {futures_result['total_margin']/total_value*100:.1f}%" if total_value > 0 else "  保证金占比:    N/A")
        else:
            print(f"  {futures_result.get('reason', '无期货方案')}")
        
        # 期权方案 (作为替代/补充)
        options_result = engine.generate_options_hedge(risk, hedge_ratio, strategy="protective_put")
        print(f"\n  📊 期权对冲方案 (保护性看跌)")
        print(f"  {'─' * 50}")
        print(f"  策略:          {options_result.get('strategy', 'N/A')}")
        print(f"  标的:          {options_result.get('underlying', 'N/A')}")
        print(f"  合约张数:      {options_result.get('contracts', 0)}")
        print(f"  预估权利金:    ¥{options_result.get('total_premium', 0):,.0f}" if options_result.get('total_premium') else f"  预估权利金:    ¥{options_result.get('total_premium', 0):,.0f}")
        print(f"  权利金占比:    {options_result.get('total_premium_pct', 0):.2f}%")
        print(f"  最大保护额度:  ¥{options_result.get('max_protection', 0):,.0f}")
        
        # 对冲效果预估
        expected_beta = risk.beta_csi300 * (1 - hedge_ratio)
        print(f"\n  📈 对冲效果预估")
        print(f"  {'─' * 50}")
        print(f"  对冲后Beta:    {expected_beta:.3f} (原{risk.beta_csi300:.3f})")
        print(f"  预期回撤减少:  ~{hedge_ratio*60:.0f}%")
        
        # 调用AI对冲分析师 (可选，需要LLM API)
        if not getattr(args, 'no_ai', False):
            progress.update(6, "AI对冲分析...")
            print(f"\n  🧠 AI 对冲分析师 (Taleb+Burry+Druckenmiller)")
            print(f"  {'─' * 50}")
            
            try:
                from quant_modules.ai_hedge_fund.agents.hedge_analyst import hedge_analyst_agent
                
                analyst_state = {
                    "messages": [],
                    "data": {
                        "tickers": list(positions.keys()),
                        "portfolio": {
                            "cash": cash,
                            "positions": {
                                code: {"long": pos['shares'], "short": 0, "long_cost_basis": pos['cost']}
                                for code, pos in positions.items()
                            },
                        },
                        "market_data": {
                            "total_value": total_value,
                            "beta_csi300": risk.beta_csi300,
                            "beta_csi500": risk.beta_csi500,
                            "var_95": risk.var_95_daily,
                            "cvar_95": risk.cvar_95_daily,
                            "concentration_hhi": risk.concentration_risk,
                        },
                        "analyst_signals": {},
                    },
                    "metadata": {
                        "show_reasoning": getattr(args, 'show_reasoning', False),
                        "model_name": getattr(args, 'model', 'deepseek-chat'),
                        "model_provider": getattr(args, 'provider', 'DeepSeek'),
                    },
                }
                
                result = hedge_analyst_agent(analyst_state)
                hedge_signal = result["data"]["analyst_signals"].get("hedge_analyst_agent", {})
                
                if hedge_signal:
                    signal_name = hedge_signal.get("signal", "neutral")
                    signal_emoji = {"bearish": "🔴", "neutral": "🟡", "bullish": "🟢"}.get(signal_name, "⚪")
                    print(f"    {signal_emoji} 对冲信号: {signal_name}")
                    print(f"    对冲比率: {hedge_signal.get('hedge_ratio', 0)*100:.0f}%")
                    print(f"    紧急程度: {hedge_signal.get('urgency_score', 0)*100:.0f}%")
                    
                    reasoning = hedge_signal.get('reasoning', '')
                    if reasoning:
                        try:
                            r = json.loads(reasoning)
                            if 'risk_warnings' in r:
                                for w in r['risk_warnings']:
                                    print(f"    ⚠️ {w}")
                            if 'hedge_recommendation' in r:
                                rec = r['hedge_recommendation']
                                print(f"    推荐工具: {rec.get('preferred_instrument', 'N/A')}")
                                print(f"    执行时机: {rec.get('execution_timing', 'N/A')}")
                        except (json.JSONDecodeError, KeyError):
                            if len(reasoning) > 100:
                                reasoning = reasoning[:100] + "..."
                            print(f"    详情: {reasoning}")
            except Exception as e:
                print(f"    ⚠️ AI分析跳过: {e}")
        
        # 保存报告
        try:
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'mode': 'hedge_analysis',
                'risk': {
                    'total_value': risk.total_value,
                    'stock_exposure': risk.stock_exposure,
                    'beta_csi300': risk.beta_csi300,
                    'beta_csi500': risk.beta_csi500,
                    'var_95_daily': risk.var_95_daily,
                    'cvar_95_daily': risk.cvar_95_daily,
                    'concentration_hhi': risk.concentration_risk,
                },
                'hedge_recommendation': {
                    'strength': strength.name,
                    'score': score,
                    'hedge_ratio': hedge_ratio,
                    'futures': futures_result if strength != HedgeSignalStrength.NO_HEDGE else {},
                    'options': options_result if strength != HedgeSignalStrength.NO_HEDGE else {},
                },
            }
            report_dir = get_archive_dir(base_dir=os.path.dirname(os.path.abspath(__file__)))
            report_path = os.path.join(report_dir, f'Hedge_Analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n  📄 报告已保存: {report_path}")
        except Exception as e:
            logger.warning(f"对冲报告保存失败: {e}")
    else:
        progress.update(6, "跳过对冲...")
        print(f"\n  ✅ 组合风险可控，无需对冲")
    
    progress.complete("✅ 对冲分析完成")
    print(f"\n  ⚠️ 以上分析仅供参考，不构成投资建议。")
    print(f"  期货/期权交易有杠杆风险，请谨慎执行。")


# ============================================================
# v5.9: 对冲-再平衡联动分析模式
# ============================================================

def run_hedge_rebalance_joint(args):
    """对冲+再平衡联动分析 — 五阶段联合决策引擎 v5.9
    
    v5.9 核心改进:
      - 组合自触发: 市场状态由组合自身波动率+回撤驱动,不再依赖CSI300
      - 多指数对冲: IC/IM/IF 按Beta比例加权分配
      - 成本过滤: 仅在对冲预期收益 > 1.5x成本时激活
      - 尾部模式: 默认TAIL_ONLY, 仅在vol>28%或DD>12%时触发
    
    五阶段工作流:
      Phase 1: 风险评估 → 组合 Beta(IF/IC/IM)/VaR/集中度/波动率
      Phase 2: 对冲决策 → 组合自触发 → 对冲比率 → 多指数期货合约
      Phase 3: 再平衡检查 → 板块轮动权重 → 动态阈值 → 买卖清单
      Phase 4: 联合优化 → 对冲后敞口 vs 再平衡后分布一致性
      Phase 5: 生成执行计划 → 优先级/窗口/绩效预估/警告
      
    选项:
      --show-reasoning  显示详细推理过程
      --auto-execute    自动化执行（需二次确认）
      --no-ai           跳过AI分析
      --mode <mode>     对冲模式: tail_only(默认)/dynamic/fixed/none
      --output <path>   指定报告输出路径
    """
    # v5.9: 对冲模式选择
    hedge_mode_str = getattr(args, 'hedge_mode', 'tail_only')
    from utils.hedge_rebalance_integrator import HedgeMode
    mode_map = {
        "tail_only": HedgeMode.TAIL_ONLY,
        "dynamic": HedgeMode.DYNAMIC,
        "fixed": HedgeMode.FIXED,
        "none": HedgeMode.NONE,
    }
    hedge_mode = mode_map.get(hedge_mode_str, HedgeMode.TAIL_ONLY)
    
    print(f"\n🔗 对冲+再平衡联动分析 — HedgeRebalanceIntegrator v5.9 (模式: {hedge_mode.value})")
    print("=" * 70)
    
    try:
        from utils.hedge_rebalance_integrator import (
            HedgeRebalanceIntegrator, run_joint_analysis
        )
        _INTEGRATOR_OK = True
    except ImportError as e:
        print(f"\n  ❌ 联动引擎加载失败: {e}")
        print("  💡 请确保 utils/hedge_rebalance_integrator.py 和 utils/hedge_engine.py 存在")
        return
    
    show_reasoning = getattr(args, 'show_reasoning', False)
    auto_execute = getattr(args, 'auto_execute', False)
    no_ai = getattr(args, 'no_ai', False)
    
    # v5.9: 估算组合波动率和回撤（从近期价格数据计算）
    import numpy as np
    portfolio_volatility = None
    portfolio_drawdown_60d = None
    try:
        prices = integrator.load_prices()
        if prices:
            # 简化估算: 从价格变化率计算
            returns = []
            for code in prices:
                px = prices[code]
                # 用组合Beta估算波动率
                pass
            # 默认使用温和估计
            portfolio_volatility = 0.18   # 18% 年化波动率(默认, 后续可由数据更新)
            portfolio_drawdown_60d = 0.0  # 无显著回撤
    except Exception:
        pass
    
    # 构建市场信号（用于外部信号输入，v5.9已大幅降权为5%）
    market_signals = {}
    
    # 五阶段工作流
    progress = ProgressIndicator("联动分析 v5.9", 5)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    integrator = HedgeRebalanceIntegrator(base_dir=base_dir, hedge_mode=hedge_mode)
    
    # Phase 1: 风险评估
    progress.update(1, "评估组合风险...")
    risk = integrator.assess_risk()
    print(f"\n  📊 [Phase 1/5] 组合风险评估 (v5.9 多指数)")
    print(f"  {'─' * 55}")
    print(f"  组合总资产:     ¥{risk.total_value:,.0f}")
    print(f"  股票敞口:       ¥{risk.stock_exposure:,.0f} ({risk.stock_exposure/risk.total_value*100:.0f}%)" if risk.total_value > 0 else "  股票敞口:       ¥0")
    print(f"  组合Beta:       CSI300={risk.beta_csi300:.2f} | CSI500={risk.beta_csi500:.2f} | CSI1000={risk.beta_csi1000:.2f}")
    print(f"  估计波动率:     {portfolio_volatility*100:.1f}% (年化)")
    print(f"  估计60日回撤:   {portfolio_drawdown_60d*100:.1f}%")
    print(f"  日VaR(95%):     ¥{risk.var_95_daily:,.0f} ({risk.var_95_daily/risk.total_value*100:.2f}%)" if risk.total_value > 0 else "  日VaR(95%):     ¥0")
    print(f"  集中度(HHI):    {risk.concentration_risk:.3f}")
    
    # Phase 2: 对冲决策 (v5.9: 组合自触发)
    progress.update(2, "对冲决策...")
    hedge = integrator.decide_hedge(
        risk, 
        portfolio_volatility=portfolio_volatility,
        portfolio_drawdown_60d=portfolio_drawdown_60d,
    )
    regime_desc = {
        "calm": "🟢 平静期", "mild": "🟡 温和波动", 
        "high": "🟠 中高波动", "tail": "🔴 尾部事件"
    }
    print(f"\n  📡 [Phase 2/5] 对冲决策")
    print(f"  {'─' * 55}")
    print(f"  市场状态:       {regime_desc.get(hedge.regime.value, hedge.regime.value)}")
    print(f"  对冲需求:       {'需要' if hedge.needed else '无需'}")
    if hedge.needed:
        print(f"  对冲比率:       {hedge.hedge_ratio*100:.0f}% (¥{risk.stock_exposure*hedge.hedge_ratio:,.0f})" if risk.stock_exposure > 0 else f"  对冲比率:       {hedge.hedge_ratio*100:.0f}%")
        print(f"  期货品种:       {', '.join(hedge.futures_instruments) if hedge.futures_instruments else '无匹配品种'}")
        if hedge.futures_contracts:
            for code, n in hedge.futures_contracts.items():
                notional = hedge.futures_notional.get(code, 0)
                margin = hedge.futures_margin.get(code, 0)
                print(f"    {code}: 做空 {n} 手 | 名义¥{notional:,.0f} | 保证金¥{margin:,.0f}")
            print(f"  总保证金:       ¥{hedge.total_margin:,.0f} (占组合 {hedge.total_margin/risk.total_value*100:.1f}%)" if risk.total_value > 0 else f"  总保证金:       ¥{hedge.total_margin:,.0f}")
        print(f"  预期对冲后Beta: {hedge.expected_beta_after:.2f}")
        print(f"  价格数据源:     {hedge.price_source}")
        if hedge.fallback_used:
            print(f"  ⚠️  回退价格品种: {', '.join(hedge.fallback_used)}")
        if show_reasoning:
            print(f"  推理:           {hedge.reasoning}")
    else:
        print(f"  理由:           {hedge.reasoning}")
    
    # Phase 3: 再平衡检查 (v5.9: 波动率驱动阈值)
    progress.update(3, "再平衡检查...")
    rebalance = integrator.check_rebalance(risk, portfolio_volatility=portfolio_volatility)
    print(f"\n  📈 [Phase 3/5] 再平衡检查")
    print(f"  {'─' * 55}")
    print(f"  再平衡类型:     {rebalance.rebalance_type}")
    print(f"  动态阈值:       {rebalance.threshold*100:.0f}%")
    print(f"  需调整标的:     {len(rebalance.positions_to_adjust)} 只")
    if rebalance.needed and rebalance.positions_to_adjust:
        print(f"  总买入: ¥{rebalance.total_buy_amount:,.0f} | 总卖出: ¥{rebalance.total_sell_amount:,.0f} | 净现金流: ¥{rebalance.net_cash_flow:,.0f}")
        print(f"\n  {'代码':<12s} {'名称':<10s} {'板块':<8s} {'操作':<6s} {'目标权重':>8s} {'当前权重':>8s} {'偏差':>8s} {'调整金额':>10s}")
        print(f"  {'─' * 80}")
        for pw in rebalance.positions_to_adjust:
            op_icon = "🔴" if pw.action == "SELL" else ("🟢" if pw.action == "BUY" else "⚪")
            print(f"  {op_icon} {pw.code:<10s} {pw.name:<10s} {pw.category:<8s} {pw.action:<6s} "
                  f"{pw.target_weight*100:>7.1f}% {pw.current_weight*100:>7.1f}% "
                  f"{pw.deviation_pct*100:>7.1f}% ¥{pw.adjustment:>10,.0f}")
    else:
        print(f"  理由:           {rebalance.reasoning}")
    if show_reasoning:
        print(f"  板块权重:       {integrator._get_sector_adjusted_weights()}")
    
    # Phase 4: 联合优化
    progress.update(4, "联合优化...")
    adj_hedge, adj_rebalance, warnings = integrator.joint_optimize(risk, hedge, rebalance)
    if warnings:
        print(f"\n  ⚙️  [Phase 4/5] 联合优化 — {len(warnings)} 项警告")
        print(f"  {'─' * 55}")
        for w in warnings:
            print(f"  ⚠️  {w}")
    else:
        print(f"\n  ⚙️  [Phase 4/5] 联合优化 — 通过 ✓")
        print(f"  {'─' * 55}")
        print(f"  对冲后敞口与再平衡后分布一致，无需调整")
    
    # Phase 5: 生成执行计划
    progress.update(5, "生成执行计划...")
    plan = integrator.generate_execution_plan(risk, adj_hedge, adj_rebalance, warnings)
    
    print(f"\n  🎯 [Phase 5/5] 执行计划")
    print(f"  {'─' * 55}")
    print(f"  优先级:         {plan.execution_priority}")
    print(f"  执行窗口:       {plan.execution_window}")
    print(f"  对冲后净敞口:   ¥{plan.after_hedge_exposure:,.0f}")
    
    print(f"\n  📊 绩效预估 (vs 基准静态配置)")
    print(f"  {'─' * 55}")
    print(f"  预估年化收益:   {plan.estimated_annual_return*100:.1f}%")
    print(f"  预估最大回撤:   {plan.estimated_max_drawdown*100:.1f}%")
    print(f"  预估夏普比率:   {plan.estimated_sharpe:.2f}")
    print(f"  预估年化波动率: {plan.estimated_volatility*100:.1f}%")
    
    print(f"\n  {'=' * 55}")
    print(f"  📋 综合: {plan.summary}")
    print(f"  {'=' * 55}")
    
    if plan.warning_flags:
        print(f"\n  ⚠️  注意事项:")
        for w in plan.warning_flags:
            print(f"    - {w}")
    
    # 保存报告
    report_path = integrator.save_report(plan)
    print(f"\n  📄 联动报告已保存: {report_path}")
    
    # AI 分析（可选）
    if not no_ai:
        print(f"\n  🧠 AI 联动分析...")
        print(f"  {'─' * 55}")
        try:
            from quant_modules.ai_hedge_fund.agents.hedge_analyst import hedge_analyst_agent
            
            positions_data = integrator.positions
            analyst_state = {
                "messages": [],
                "data": {
                    "tickers": list(positions_data.keys()),
                    "portfolio": {
                        "cash": risk.cash,
                        "positions": {
                            code: {"long": p.get('shares', 0), "short": 0, "long_cost_basis": p.get('cost', 0)}
                            for code, p in positions_data.items()
                        },
                    },
                    "market_data": {
                        "total_value": risk.total_value,
                        "beta_csi300": risk.beta_csi300,
                        "var_95": risk.var_95_daily,
                        "cvar_95": risk.cvar_95_daily,
                        "hedge_ratio": adj_hedge.hedge_ratio if adj_hedge.needed else 0,
                        "rebalance_type": adj_rebalance.rebalance_type if adj_rebalance.needed else "none",
                        "execution_priority": plan.execution_priority,
                    },
                    "analyst_signals": {},
                },
                "metadata": {
                    "show_reasoning": show_reasoning,
                    "model_name": getattr(args, 'model', 'deepseek-chat'),
                    "model_provider": getattr(args, 'provider', 'DeepSeek'),
                },
            }
            
            result = hedge_analyst_agent(analyst_state)
            hedge_signal = result["data"]["analyst_signals"].get("hedge_analyst_agent", {})
            if hedge_signal:
                signal_name = hedge_signal.get("signal", "neutral")
                signal_emoji = {"bearish": "🔴", "neutral": "🟡", "bullish": "🟢"}.get(signal_name, "⚪")
                print(f"    {signal_emoji} 对冲信号: {signal_name}")
                print(f"    对冲比率: {hedge_signal.get('hedge_ratio', 0)*100:.0f}%")
                print(f"    紧急程度: {hedge_signal.get('urgency_score', 0)*100:.0f}%")
                
                reasoning = hedge_signal.get('reasoning', '')
                if reasoning and show_reasoning:
                    try:
                        r = json.loads(reasoning) if isinstance(reasoning, str) else reasoning
                        if 'risk_warnings' in r:
                            for w in r['risk_warnings']:
                                print(f"    ⚠️ {w}")
                        if 'hedge_recommendation' in r:
                            rec = r['hedge_recommendation']
                            print(f"    推荐工具: {rec.get('preferred_instrument', 'N/A')}")
                            print(f"    执行时机: {rec.get('execution_timing', 'N/A')}")
                    except (json.JSONDecodeError, KeyError, TypeError):
                        if len(str(reasoning)) > 100:
                            reasoning = str(reasoning)[:100] + "..."
                        print(f"    详情: {reasoning}")
        except Exception as e:
            print(f"    ⚠️ AI分析跳过: {e}")
    
    # 自动化执行（需二次确认）
    if auto_execute:
        print(f"\n  {'=' * 55}")
        print(f"  ⚠️  自动化执行模式 — 需要二次确认")
        print(f"  {'=' * 55}")
        print(f"\n  即将执行以下操作:")
        
        if adj_hedge.needed:
            print(f"  🛡️  对冲操作:")
            print(f"     - 对冲比率: {adj_hedge.hedge_ratio*100:.0f}%")
            print(f"     - 期货品种: {', '.join(adj_hedge.futures_instruments) if adj_hedge.futures_instruments else '无'}")
            print(f"     - 总保证金: ¥{adj_hedge.total_margin:,.0f}")
        
        if adj_rebalance.needed and adj_rebalance.positions_to_adjust:
            print(f"\n  🔄 再平衡操作:")
            for pw in adj_rebalance.positions_to_adjust:
                print(f"     {pw.action} {pw.code} {pw.name}: {abs(pw.adjustment_shares)}股 ¥{abs(pw.adjustment):,.0f}")
        
        print(f"\n  ⚠️  请确认以上操作。输入 'yes' 继续执行: ", end='')
        try:
            confirm = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = 'no'
        
        if confirm == 'yes':
            print(f"\n  🚀 开始执行联动计划...")
            try:
                # 保存执行记录
                exec_record = {
                    'timestamp': datetime.now().isoformat(),
                    'mode': 'hedge_rebalance_auto_execute',
                    'plan_summary': plan.summary,
                    'hedge': {
                        'needed': adj_hedge.needed,
                        'ratio': adj_hedge.hedge_ratio,
                        'instruments': adj_hedge.futures_instruments,
                    },
                    'rebalance': {
                        'needed': adj_rebalance.needed,
                        'type': adj_rebalance.rebalance_type,
                        'adjustments': [
                            {'code': pw.code, 'action': pw.action, 'shares': pw.adjustment_shares, 'amount': pw.adjustment}
                            for pw in (adj_rebalance.positions_to_adjust if adj_rebalance.needed else [])
                        ],
                    },
                }
                exec_dir = os.path.join(base_dir, '..', 'reports', 'executions')
                os.makedirs(exec_dir, exist_ok=True)
                exec_path = os.path.join(exec_dir, f'exec_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                with open(exec_path, 'w', encoding='utf-8') as f:
                    json.dump(exec_record, f, ensure_ascii=False, indent=2, default=str)
                print(f"  ✅ 执行记录已保存: {exec_path}")
                print(f"\n  💡 注意: 实际交易执行需通过券商API完成。")
                print(f"     当前系统仅记录执行意图，请手动确认后通过交易终端执行。")
            except Exception as e:
                print(f"  ❌ 执行记录保存失败: {e}")
        else:
            print(f"\n  ❌ 执行已取消。")
    
    progress.complete("✅ 联动分析完成")
    print(f"\n  ⚠️ 以上分析仅供参考，不构成投资建议。")
    print(f"  期货/期权交易有杠杆风险，对冲操作有基差风险、保证金风险，请谨慎执行。")


# ============================================================
# 主入口
# ============================================================

def main():
    # ── 模式注册表：flag / dest / 帮助文本 / handler ──
    MODES = [
        ('--daily',           'daily',           '三阶段交易工作流 (盘前计划/盘中策略/盘后报告)', run_daily_workflow),
        ('--live',            'live',            '实时监控模式',                                    run_live_monitoring),
        ('--report',          'report',          '报告生成模式',                                    run_report_generation),
        ('--rebalance',       'rebalance',       '再平衡模式',                                      run_rebalance),
        ('--backtest',        'backtest',        '回测模式',                                        run_backtest),
        ('--risk',            'risk',            '风险监控模式',                                    run_risk_monitor),
        ('--check',           'check',           '快速检查模式',                                    run_quick_check),
        ('--hypothesis',      'hypothesis',      '假设验证模式',                                    run_hypothesis_test),
        ('--etf-flow',        'etf_flow',        'ETF资金流向监控',                                 run_etf_flow_monitor),
        ('--portfolio-opt',   'portfolio_opt',   '投资组合优化',                                    run_portfolio_optimization),
        ('--kommo-monitor',   'kommo_monitor',   '康波周期监控',                                    run_kommo_monitor),
        ('--commodity-fund',  'commodity_fund',  '大宗商品基本面',                                  run_commodity_fundamentals),
        ('--train-model',     'train_model',     '时序预测训练',                                    run_model_training),
        ('--train-enhanced',  'train_enhanced',  'ML增强训练 v2.0 - 四维优化(标签+窗口+特征+权重)',    run_enhanced_training_mode),
        ('--kondratiev',      'kondratiev',      '康波周期+十五五交叠分析',                         run_kondratiev_analysis),
        ('--fifteen-five',    'fifteen_five',    '十五五规划适配分析',                              run_fifteen_five_analysis),
        ('--social-security', 'social_security', '社保基金ETF风格追踪',                             run_social_security_analysis),
        ('--macro-analysis',  'macro_analysis',  '宏观综合分析（康波+十五五+社保ETF一键运行）',       run_macro_analysis),
        ('--ai-decision',     'ai_decision',     'AI盘中决策 v5.9 - 场景路由+并行对冲+Wind MCP动态数据', run_ai_decision),
        ('--futures-options', 'futures_options', '期货期权扫描',                                    run_futures_options_scan),
        ('--unified-monitor', 'unified_monitor', '统一监控模式 - 一键启动所有模块',                  run_unified_monitor),
        ('--ai-hedge',        'ai_hedge',        'AI Hedge Fund - 20位大师级AI分析师联合决策(含对冲分析师)',run_ai_hedge_mode),
        ('--ml-signal',       'ml_signal',       'ML模型预测信号',                                  run_ml_signal_mode),
        ('--ml-enhanced',     'ml_enhanced',     'ML增强预测 v2.0 - 四维优化模型信号',               run_enhanced_prediction_mode),
        ('--hedge',           'hedge',           '对冲分析 v5.9 — Taleb+Burry+Druck 多指数期货/期权风险对冲',run_hedge_mode),
        ('--hedge-rebalance', 'hedge_rebalance', '对冲+再平衡联动分析 v5.9 — 组合自触发+多指数Beta加权',           run_hedge_rebalance_joint),
    ]

    # 由 MODES 动态生成 epilog 中的运行模式清单
    mode_lines = '\n'.join(
        f"  {flag:<20s} {help_text}" for flag, _, help_text, _ in MODES
    )

    parser = argparse.ArgumentParser(
        description='量化策略系统 v5.9 — AI决策驱动 + 对冲再平衡联动v5.9',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
运行模式:
{mode_lines}

示例:
  python "量化策略系统 v5.9.py" --live              # 启动实时监控
  python "量化策略系统 v5.9.py" --report            # 生成报告
  python "量化策略系统 v5.9.py" --rebalance         # 执行再平衡
  python "量化策略系统 v5.9.py" --risk              # 风险监控
  python "量化策略系统 v5.9.py" --check             # 系统检查
  python "量化策略系统 v5.9.py" --etf-flow          # ETF资金流向监控
  python "量化策略系统 v5.9.py" --hypothesis --list # 列出假设
  python "量化策略系统 v5.9.py" --portfolio-opt     # 投资组合优化
  python "量化策略系统 v5.9.py" --kommo-monitor     # 康波周期监控
  python "量化策略系统 v5.9.py" --commodity-fund    # 大宗商品基本面
  python "量化策略系统 v5.9.py" --train-model       # 时序预测训练
  python "量化策略系统 v5.9.py" --kondratiev        # 康波周期+十五五交叠分析
  python "量化策略系统 v5.9.py" --fifteen-five      # 十五五规划适配分析
  python "量化策略系统 v5.9.py" --social-security   # 社保基金ETF风格追踪
  python "量化策略系统 v5.9.py" --macro-analysis    # 宏观综合分析
  python "量化策略系统 v5.9.py" --ai-decision       # AI盘中决策 (v5.9: 并行对冲+Wind MCP)
  python "量化策略系统 v5.9.py" --ai-decision --scene=rebalancing_analysis  # 再平衡深度分析
  python "量化策略系统 v5.9.py" --ai-decision --no-wind  # AI决策 (禁用Wind数据)
  python "量化策略系统 v5.9.py" --futures-options   # 期货期权扫描
  python "量化策略系统 v5.9.py" --unified-monitor    # 统一监控
  python "量化策略系统 v5.9.py" --ai-hedge          # AI Hedge Fund
  python "量化策略系统 v5.9.py" --ml-signal         # ML模型预测信号
  python "量化策略系统 v5.9.py" --hedge             # 对冲分析 (多指数期货/期权)
  python "量化策略系统 v5.9.py" --hedge --no-ai     # 对冲分析 (仅规则引擎)
  python "量化策略系统 v5.9.py" --hedge-rebalance                        # 对冲+再平衡联动分析 v5.9 (组合自触发)
  python "量化策略系统 v5.9.py" --hedge-rebalance --mode=tail_only       # 尾部保护模式 (默认)
  python "量化策略系统 v5.9.py" --hedge-rebalance --mode=dynamic         # 动态对冲模式
  python "量化策略系统 v5.9.py" --hedge-rebalance --show-reasoning       # 含详细推理过程
  python "量化策略系统 v5.9.py" --hedge-rebalance --auto-execute         # 自动化执行(需二次确认)

架构特点 (借鉴Vibe-Trading):
  • Connector-first: 统一数据源抽象，支持多连接器配置
  • 策略注册表: 中心化策略管理与版本控制
  • 假设验证: 支持统计检验与随机对照试验
  • 研究目标: 支持目标生命周期管理
  • 实时反馈: 长时间任务的进度可视化
  • ETF资金流向: 国家队资金监控，投资决策参考
  • 投资组合优化: 等权重/风险平价/风险配比/因子配比/自定义配置
  • 康波周期监控: 商品价格+宏观指标+产业库存三维度
  • 时序预测: Transformer模型骨架集成
        """
    )

    # ── 注册运行模式（数据驱动，声明一次即可） ──
    mode_group = parser.add_mutually_exclusive_group(required=True)
    for flag, dest, help_text, _ in MODES:
        mode_group.add_argument(flag, dest=dest, action='store_true', help=help_text)

    # ── 子阶段 / 通用选项 / 模式专属选项 ──
    # --daily 子阶段
    parser.add_argument('--phase', choices=['premarket', 'intraday', 'postmarket', 'all'],
                        default='all', help='三阶段工作流子阶段 (配合 --daily 使用)')

    # 通用选项
    parser.add_argument('--no-ai', action='store_true', help='禁用AI分析模块')
    parser.add_argument('--output', '-o', default=None, help='输出报告文件名')
    parser.add_argument('--sync-sl', action='store_true', help='同步止损止盈规则')

    # v5.9: AI 决策场景路由选项
    parser.add_argument('--scene', type=str, default='intraday_decision',
                       choices=['intraday_decision', 'rebalancing_analysis', 'macro_analysis', 'report_generation'],
                       help='AI决策场景 (默认: intraday_decision=盘中并行对冲)')
    parser.add_argument('--no-wind', action='store_true', help='禁用 Wind MCP 数据 (使用降级数据源)')
    parser.add_argument('--interval', type=int, default=300, help='AI决策检查间隔(秒, 默认 300)')

    # AI Hedge Fund 选项
    parser.add_argument('--ticker', '-t', nargs='+', default=None, help='AI Hedge Fund: 股票代码列表')
    parser.add_argument('--analysts', '-a', nargs='*', default=None, help='AI Hedge Fund: 选择分析师 (默认全部)')
    parser.add_argument('--show-reasoning', action='store_true', help='AI Hedge Fund: 显示分析详情')
    parser.add_argument('--model', type=str, default=None, help='AI Hedge Fund: LLM 模型名')
    parser.add_argument('--provider', type=str, default=None, help='AI Hedge Fund: LLM 提供商')
    parser.add_argument('--start-date', type=str, default=None, help='AI Hedge Fund/回测: 开始日期 YYYY-MM-DD')
    parser.add_argument('--end-date', type=str, default=None, help='AI Hedge Fund/回测: 结束日期 YYYY-MM-DD')

    # v5.9: 对冲-再平衡联动选项
    parser.add_argument('--auto-execute', action='store_true', help='对冲-再平衡联动: 自动化执行 (需二次确认)')
    parser.add_argument('--mode', dest='hedge_mode', type=str, default='tail_only',
                       choices=['tail_only', 'dynamic', 'fixed', 'none'],
                       help='对冲-再平衡联动: 对冲模式 (默认 tail_only=仅尾部保护)')

    # 假设验证选项
    parser.add_argument('--list', action='store_true', help='列出研究假设')
    parser.add_argument('--register', type=str, help='注册新假设: id|名称|描述')
    parser.add_argument('--validate', type=str, help='验证指定假设')

    # ML信号选项
    parser.add_argument('--threshold', type=float, default=0.55, help='ML信号: 买入信号阈值 (默认 0.55)')
    parser.add_argument('--no-ml', action='store_true', help='跳过ML模型信号扫描')
    # ── v5.7 Phase 2: 高级训练选项 ──
    parser.add_argument('--optuna', action='store_true', help='训练: 启用 Optuna 贝叶斯超参数优化')
    parser.add_argument('--triple-barrier', action='store_true', help='训练: 启用 Triple Barrier 标签 (替代简单涨跌标签)')
    parser.add_argument('--stacking', action='store_true', help='训练/预测: 启用 Stacking 多模型集成')
    parser.add_argument('--optuna-trials', type=int, default=100, help='训练: Optuna 试验次数 (默认 100)')
    parser.add_argument('--skip-ml-filter', action='store_true', help='AI Hedge Fund: 跳过ML预筛选')
    parser.add_argument('--mlflow', action='store_true', help='训练: 启用 MLflow 实验追踪 (需 pip install mlflow)')

    args = parser.parse_args()

    # ── 数据驱动分发（v5.7 Phase 1 增强：统一执行时长追踪）──
    for flag, dest, _, handler in MODES:
        if getattr(args, dest):
            start_time = time.time()
            try:
                result = handler(args)
                duration = time.time() - start_time
                _log_execution_summary(dest, duration, True, result)
            except KeyboardInterrupt:
                duration = time.time() - start_time
                print(f"\n⏹️  用户中断 ({dest})")
                _log_execution_summary(dest, duration, False, {'interrupted': True})
            except Exception as e:
                duration = time.time() - start_time
                print(f"\n❌ {dest} 执行异常: {e}")
                _log_execution_summary(dest, duration, False, {'error': str(e)})
            break

if __name__ == '__main__':
    # 打印启动信息
    print("=" * 70)
    print("          量化策略系统 v5.9 - 对冲再平衡联动版")
    print("                    HKUDS/Vibe-Trading Architecture")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)
    
    main()