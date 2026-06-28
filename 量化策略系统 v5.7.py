# -*- coding: utf-8 -*-
"""
量化策略系统 v5.7- 康波周期 + 十五五规划 + 社保基金ETF追踪 优化版
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
  5. 止损止盈风险监控 (基于Excel配置的动态止损)
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

Excel数据源 (5个表格联动):
  - data_extraction_complete_rebalancing_plan.xlsx: 16只标的完整计划
  - data_extraction_batch_execution_plan.xlsx: 分批执行计划
  - data_extraction_execution_summary_and_tips.xlsx: 执行策略建议
  - data_extraction_fund_flow_summary.xlsx: 资金流向汇总
  - data_extraction_portfolio_comparison_analysis.xlsx: 组合对比分析

运行模式:
  - 实时监控模式: 盘中实时行情监控 + 自动再平衡
  - 报告生成模式: 生成每日持仓报告
  - 回测模式: 历史数据回测验证
  - 再平衡模式: 执行Excel驱动的再平衡计划
  - 风险监控模式: 止损止盈状态检查
  - ETF资金流向: 追踪国家队资金动向
  - 假设验证模式: 验证交易假设
  - 投资组合优化: 多策略资产配置对比 (新增)
  - 康波周期监控: 大宗商品全维度监控 (新增)
  - 大宗商品基本面: Wind数据综合分析 (新增)
  - 时序预测训练: Transformer模型训练 (新增)

使用方式:
  python "量化策略系统 v5.7.py" --daily --phase premarket   # 盘前交易计划
  python "量化策略系统 v5.7.py" --daily --phase intraday    # 盘中策略扫描
  python "量化策略系统 v5.7.py" --daily --phase postmarket  # 盘后综合报告
  python "量化策略系统 v5.7.py" --daily --phase all         # 全流程
  python "量化策略系统 v5.7.py" --rebalance      # 执行Excel再平衡
  python "量化策略系统 v5.7.py" --rebalance --sync-sl  # 同步止损止盈
  python "量化策略系统 v5.7.py" --live           # 实时监控模式
  python "量化策略系统 v5.7.py" --report         # 生成报告
  python "量化策略系统 v5.7.py" --etf-flow       # ETF资金流向监控
  python "量化策略系统 v5.7.py" --portfolio-opt  # 投资组合优化
  python "量化策略系统 v5.7.py" --kommo-monitor  # 康波周期监控
  python "量化策略系统 v5.7.py" --commodity-fund # 大宗商品基本面
  python "量化策略系统 v5.7.py" --train-model    # 时序预测训练
  python "量化策略系统 v5.7.py" --kondratiev     # 康波周期+十五五交叠分析 (v5.1)
  python "量化策略系统 v5.7.py" --fifteen-five   # 十五五规划适配分析 (v5.1)
  python "量化策略系统 v5.7.py" --social-security # 社保基金ETF风格追踪 (v5.1)
  python "量化策略系统 v5.7.py" --macro-analysis  # 宏观综合分析（一键运行三大）(v5.1)
  python "量化策略系统 v5.7.py" --ml-signal       # ML模型预测信号 - GradientBoosting涨跌预测 (v5.6新增)

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
import argparse
import time
from datetime import datetime, time as dt_time
from typing import Dict, Any, Optional, List

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
    from utils.ml_predictor import MLModelPredictor, run_ml_signal_scan
    ML_PREDICTOR_AVAILABLE = True
    logger.info("✅ ML模型预测模块已加载")
except ImportError as e:
    MLModelPredictor = None
    run_ml_signal_scan = None
    ML_PREDICTOR_AVAILABLE = False
    logger.warning(f"⚠️ ML模型预测模块加载失败: {e}")

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
    """实时监控模式 - 盘中实时行情监控 + 自动再平衡"""
    print("\n🚀 启动实时监控模式")
    print("=" * 70)
    
    progress = ProgressIndicator("初始化系统", 5)
    
    progress.update(1, "加载交易系统...")
    AutoTradingSystem = auto_trading.get('AutoTradingSystem')
    
    if AutoTradingSystem:
        progress.update(2, "创建交易实例...")
        system = AutoTradingSystem()
        
        progress.update(3, "连接数据源...")
        # 尝试连接优先数据源
        
        progress.update(4, "启动监控循环...")
        system.run()
        progress.complete("监控结束")
    else:
        progress.complete("❌ 自动交易系统模块不可用")

def run_report_generation(args):
    """报告生成模式 - 生成每日持仓报告"""
    print("\n📝 生成每日报告")
    print("=" * 70)
    
    progress = ProgressIndicator("生成报告", 5)
    
    progress.update(1, "加载报告模块...")
    generate_daily_report = daily_report.get('generate_daily_report')
    
    if generate_daily_report:
        try:
            progress.update(2, "读取配置...")
            portfolio_file = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
            
            progress.update(3, "生成报告内容...")
            report_content = generate_daily_report(
                portfolio_file=portfolio_file,
                enable_ai_analysis=not args.no_ai
            )
            
            progress.update(4, "保存报告...")
            # 归档到每日报告目录（保持 .txt 扩展名）
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
    """时序预测模型训练模式 - Transformer模型"""
    print("\n🤖 时序预测模型训练")
    print("=" * 70)
    
    progress = ProgressIndicator("模型训练", 4)
    
    progress.update(1, "检查依赖库...")
    missing = []
    for pkg in ('torch', 'sklearn', 'pandas', 'numpy'):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        progress.complete(f"❌ 缺少依赖包: {missing}")
        print(f"\n请安装: pip install {' '.join(missing)}")
        return None
    
    progress.update(2, "加载Transformer模型骨架...")
    try:
        # 尝试导入未命名.py中的模型训练功能
        sys.path.insert(0, os.path.join(BASE_DIR, '..', '03_投研与策略生成'))
        from 未命名 import create_model, train, DATA_PATH, MODEL_PATH
        
        # 检查数据文件是否存在
        if not DATA_PATH.exists():
            progress.complete(f"❌ 数据文件不存在: {DATA_PATH}")
            print(f"\n请修改 DATA_PATH 为实际CSV数据路径")
            print(f"数据文件必须包含列: close, volume, inventory_qhd, power_plant_consumption, temperature, precipitation")
            return None
        
        progress.update(3, "开始训练模型...")
        model, scaler = train(data_path=DATA_PATH, model_path=MODEL_PATH)
        
        progress.update(4, "保存模型...")
        print(f"\n✅ 模型已保存到: {MODEL_PATH}")
        progress.complete("✅ 模型训练完成")
        
        return model, scaler
        
    except Exception as e:
        progress.complete(f"❌ 模型训练失败: {e}")
        logger.error(f"训练失败: {e}")
        return None


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
    # 尝试获取ETF资金流数据用于强化分析
    flow_data = None
    try:
        flow_monitor = ETFFundFlowMonitor(data_connector_manager=connector_manager)
        flow_monitor.analyze_fund_flow()
        flow_data = _build_etf_flow_data(flow_monitor)
        if flow_data:
            print(f"\n  💰 已获取 {len(flow_data)} 只ETF资金流数据")
    except Exception as e:
        logger.debug(f"获取ETF资金流数据失败（将使用静态分析）: {e}")

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

            # 获取实时的ETF资金流数据
            flow_data = None
            try:
                flow_monitor = ETFFundFlowMonitor(data_connector_manager=connector_manager)
                flow_monitor.analyze_fund_flow()
                flow_data = _build_etf_flow_data(flow_monitor)
            except Exception:
                pass

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
    """GLM5 AI盘中实时决策模式 - 使用AI分析市场并生成交易决策"""
    print("\n🤖 GLM-5 AI 盘中实时决策模式")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)

    try:
        from utils.intraday_decision import IntradayDecisionMonitor

        # 创建监控器（使用豆包Speed，最快响应）
        monitor = IntradayDecisionMonitor(
            api_model='doubao-speed-32k',
            check_interval=300,
            enable_notifications=True,
        )

        # 加载持仓
        if not monitor.load_positions():
            print("❌ 持仓数据加载失败,请检查 config/positions.json")
            return

        print(f"✅ 已加载 {len(monitor.positions)} 只持仓")

        # 生成决策
        print("\n📊 正在调用GLM5生成交易决策...")
        print("   (这需要10-30秒,请耐心等待)")
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
            for sig in decision.trading_signals:
                action_map = {'BUY': '买入', 'SELL': '卖出', 'HOLD': '持有', 'REDUCE': '减仓'}
                action_cn = action_map.get(sig.action, sig.action)
                print(f"   [{action_cn}] {sig.code} {sig.name}")
                print(f"      理由: {sig.reason[:100]}")
                print(f"      置信度: {sig.confidence:.2f}, 紧急程度: {sig.urgency}")
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
        print("❌ GLM5决策模块未安装")
        print("   请确保 utils/glm5_decision_engine.py 和 utils/glm5_client.py 存在")
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
                print("\n✅ 全流程执行完成")
            else:
                # 手动串联三个阶段
                for i, (func_name, success_msg) in enumerate(PHASE_MAP.values(), 1):
                    print(f"\n[{i}/{len(PHASE_MAP)}] {success_msg[:4]}")
                    func = getattr(dtw, func_name, None)
                    if func:
                        func()

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
    """统一监控模式 - 一键启动所有模块"""
    print("\n🎯 统一监控模式")
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
    
    # 启动线程
    threads = []
    modules_config = [
        ("股票实时监控", stock_monitor_func, 300),
        ("期货期权扫描", futures_scan_func, 180),
        ("风险评估", risk_check_func, 300)
    ]
    
    print("\n" + "=" * 70)
    print("📋 已注册模块:")
    print("=" * 70)
    for name, _, interval in modules_config:
        print(f"  - {name}: 每 {interval}秒")
    
    print("\n" + "=" * 70)
    print("🔥 开始并行启动所有模块...")
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
        time.sleep(1)
    
    print("\n" + "=" * 70)
    print("✅ 所有模块已启动！")
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
        ('--kondratiev',      'kondratiev',      '康波周期+十五五交叠分析',                         run_kondratiev_analysis),
        ('--fifteen-five',    'fifteen_five',    '十五五规划适配分析',                              run_fifteen_five_analysis),
        ('--social-security', 'social_security', '社保基金ETF风格追踪',                             run_social_security_analysis),
        ('--macro-analysis',  'macro_analysis',  '宏观综合分析（康波+十五五+社保ETF一键运行）',       run_macro_analysis),
        ('--ai-decision',     'ai_decision',     'GLM5 AI盘中实时决策模式',                         run_ai_decision),
        ('--futures-options', 'futures_options', '期货期权扫描',                                    run_futures_options_scan),
        ('--unified-monitor', 'unified_monitor', '统一监控模式 - 一键启动所有模块',                  run_unified_monitor),
        ('--ai-hedge',        'ai_hedge',        'AI Hedge Fund - 19位大师级AI分析师联合决策',      run_ai_hedge_mode),
        ('--ml-signal',       'ml_signal',       'ML模型预测信号 - GradientBoosting涨跌预测',       run_ml_signal_mode),
    ]

    # 由 MODES 动态生成 epilog 中的运行模式清单
    mode_lines = '\n'.join(
        f"  {flag:<20s} {help_text}" for flag, _, help_text, _ in MODES
    )

    parser = argparse.ArgumentParser(
        description='量化策略系统 v5.7 - Vibe-Trading 优化版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
运行模式:
{mode_lines}

示例:
  python "量化策略系统 v5.7.py" --live              # 启动实时监控
  python "量化策略系统 v5.7.py" --report            # 生成报告
  python "量化策略系统 v5.7.py" --rebalance         # 执行再平衡
  python "量化策略系统 v5.7.py" --risk              # 风险监控
  python "量化策略系统 v5.7.py" --check             # 系统检查
  python "量化策略系统 v5.7.py" --etf-flow          # ETF资金流向监控
  python "量化策略系统 v5.7.py" --hypothesis --list # 列出假设
  python "量化策略系统 v5.7.py" --portfolio-opt     # 投资组合优化
  python "量化策略系统 v5.7.py" --kommo-monitor     # 康波周期监控
  python "量化策略系统 v5.7.py" --commodity-fund    # 大宗商品基本面
  python "量化策略系统 v5.7.py" --train-model       # 时序预测训练
  python "量化策略系统 v5.7.py" --kondratiev        # 康波周期+十五五交叠分析
  python "量化策略系统 v5.7.py" --fifteen-five      # 十五五规划适配分析
  python "量化策略系统 v5.7.py" --social-security   # 社保基金ETF风格追踪
  python "量化策略系统 v5.7.py" --macro-analysis    # 宏观综合分析
  python "量化策略系统 v5.7.py" --ai-decision       # AI盘中实时决策
  python "量化策略系统 v5.7.py" --futures-options   # 期货期权扫描
  python "量化策略系统 v5.7.py" --unified-monitor    # 统一监控
  python "量化策略系统 v5.7.py" --ai-hedge          # AI Hedge Fund
  python "量化策略系统 v5.7.py" --ml-signal         # ML模型预测信号

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

    # AI Hedge Fund 选项
    parser.add_argument('--ticker', '-t', nargs='+', default=None, help='AI Hedge Fund: 股票代码列表')
    parser.add_argument('--analysts', '-a', nargs='*', default=None, help='AI Hedge Fund: 选择分析师 (默认全部)')
    parser.add_argument('--show-reasoning', action='store_true', help='AI Hedge Fund: 显示分析详情')
    parser.add_argument('--model', type=str, default=None, help='AI Hedge Fund: LLM 模型名')
    parser.add_argument('--provider', type=str, default=None, help='AI Hedge Fund: LLM 提供商')
    parser.add_argument('--start-date', type=str, default=None, help='AI Hedge Fund/回测: 开始日期 YYYY-MM-DD')
    parser.add_argument('--end-date', type=str, default=None, help='AI Hedge Fund/回测: 结束日期 YYYY-MM-DD')

    # 假设验证选项
    parser.add_argument('--list', action='store_true', help='列出研究假设')
    parser.add_argument('--register', type=str, help='注册新假设: id|名称|描述')
    parser.add_argument('--validate', type=str, help='验证指定假设')

    # ML信号选项
    parser.add_argument('--threshold', type=float, default=0.55, help='ML信号: 买入信号阈值 (默认 0.55)')

    args = parser.parse_args()

    # ── 数据驱动分发（取代 22 分支 if/elif） ──
    for _, dest, _, handler in MODES:
        if getattr(args, dest):
            handler(args)
            break

def run_ai_hedge_mode(args):
    """AI Hedge Fund — 19位大师级AI分析师联合决策模式"""
    # 懒加载以支持无 langchain 环境正常运行其他 CLI 模式
    try:
        from quant_modules.ai_hedge_fund.orchestrator import (
            run_ai_hedge_fund, print_trading_output, get_available_analysts
        )
    except ImportError as e:
        print(f"❌ AI Hedge Fund 模块不可用: {e}")
        print("   请安装依赖: pip install langgraph langchain langchain-openai python-dotenv")
        return

    print("=" * 70)
    print("  🤖 AI Hedge Fund — 多分析师联合决策系统")
    print("  19位大师级AI分析师 + 风控 + 组合管理")
    print("=" * 70)

    # 获取标的
    tickers = []
    if hasattr(args, 'ticker') and args.ticker:
        tickers = args.ticker
    else:
        # 默认使用持仓中的股票
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

    print(f"\n  分析标的: {', '.join(tickers)}")

    # 选择分析师
    if hasattr(args, 'analysts') and args.analysts:
        selected = args.analysts
    else:
        selected = None  # 使用全部

    # 获取可选分析师列表
    available = get_available_analysts()
    print(f"  可用分析师: {len(available)} 位")
    if selected:
        print(f"  已选择: {', '.join(selected)}")

    # 运行分析
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

    # 保存报告
    try:
        import json
        report = {
            'timestamp': datetime.now().isoformat(),
            'mode': 'ai_hedge',
            'tickers': tickers,
            'decisions': result.get('decisions', {}),
            'analyst_signals': result.get('analyst_signals', {}),
        }
        report_dir = get_archive_dir(base_dir=os.path.dirname(os.path.abspath(__file__)))
        report_path = os.path.join(report_dir, f'AI_Hedge_Fund_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n  📄 报告已保存: {report_path}")
    except Exception as e:
        logger.warning(f"报告保存失败: {e}")


if __name__ == '__main__':
    # 打印启动信息
    print("=" * 70)
    print("          量化策略系统 v5.7 - Vibe-Trading 优化版")
    print("                    HKUDS/Vibe-Trading Architecture")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)
    
    main()