# -*- coding: utf-8 -*-
"""运行模式调度模块

从主文件抽取所有 run_* 运行模式函数、main() 入口和辅助代码。
依赖: bootstrap.py（公共引导模块）、engine.data / engine.rebalance（数据引擎）。
"""

import os
import sys
import argparse
import time
import json
import numpy as np
from datetime import datetime, time as dt_time
from typing import Dict, Any, Optional, List

from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import json as _json
from bootstrap import BASE_DIR, logger, event_tracker, setup_logging, get_logger
from bootstrap import (
    PerformanceTracker, StrategyRegistry,
    QuantSystemError, DataSourceError, ConfigError, TradingError, ValidationError,
    GracefulFallback, handle_exception,
)
from quant_modules.core import ModuleLoader, ConfigManager, load_portfolio_config, ProgressIndicator
from quant_modules.data_layer import DataCache, DataConnector, DataConnectorManager
from engine.rebalance import ExcelDrivenRebalancingEngineV4
from engine.managers import (
    PortfolioOptimizationEngine, KommoCommodityMonitor, ETFFundFlowMonitor,
)
from utils.report_archiver import archive_report, get_archive_dir

# ============================================================
# 新增模块: ETF资金流 + 社保基金风格追踪 (v5.2增强)
# ============================================================
try:
    from engine.etf_flow import ETFRealTimeTracker, NATIONAL_TEAM_ETFS as _etf_list
    ETF_FLOW_AVAILABLE = True
    logger.info("[mode] engine.etf_flow 模块加载成功")
except Exception as _e:
    ETF_FLOW_AVAILABLE = False
    logger.warning(f"[mode] engine.etf_flow 加载失败: {_e}")
    ETFRealTimeTracker = None  # type: ignore

try:
    from engine.social_security import (
        SocialSecurityStyleTracker,
        STYLE_DEFINITIONS as _style_defs,
        run_tracking_summary as _ss_run,
    )
    SOCIAL_SECURITY_V2_AVAILABLE = True
    logger.info("[mode] engine.social_security 模块加载成功")
except Exception as _e:
    SOCIAL_SECURITY_V2_AVAILABLE = False
    logger.warning(f"[mode] engine.social_security 加载失败: {_e}")

# ============================================================
# 模块导入 (优雅降级)
# ============================================================

class ModuleLoader:
    """模块加载器，支持优雅降级"""

    def __init__(self):
        self._modules = {}

    def load(self, module_name, import_dict):
        """尝试加载模块，失败时记录但不抛出异常"""
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
        except Exception as e:
            logger.warning(f"模块 {module_name} 初始化失败: {e}")
            return {alias: None for alias in import_dict.values()}

# 加载核心模块
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
# LSEG MCP 连接器集成 (优先级3) - 已禁用
# 配置管理 - 统一配置管理器
# ============================================================
config_manager = ConfigManager()


# 从原文件导入尚未抽取到独立模块的大类
# ============================================================

ETFFundFlowMonitor = None
KommoCommodityMonitor = None
PortfolioOptimizationEngine = None
# 进度显示工具


# ============================================================
# 辅助函数
# ============================================================

def _check_commodity_module():
    """检查大宗商品基本面模块是否可用"""
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, '..', '03_投研与策略生成'))
        from 大宗商品基本面综合 import get_copper_fundamentals
        return callable(get_copper_fundamentals)
    except Exception:
        return False


# ============================================================
# 运行模式实现
# ============================================================

def run_daily_workflow(args):
    """三阶段交易工作流 — 盘前计划 + 盘中策略 + 盘后报告"""
    try:
        from daily_trading_workflow import (
            run_premarket, run_intraday, run_postmarket, run_all
        )
        phase = getattr(args, 'phase', 'all')
        print("\n📋 三阶段交易工作流引擎")
        print("=" * 70)
        if phase == 'premarket':
            run_premarket()
        elif phase == 'intraday':
            run_intraday()
        elif phase == 'postmarket':
            run_postmarket()
        elif phase == 'all':
            run_all()
    except ImportError as e:
        print(f"\n❌ 三阶段工作流模块不可用: {e}")
        print("请确保 daily_trading_workflow.py 存在于 11_量化策略 目录中")

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

    # 保存报告
    if args.output:
        report_dir = os.path.join(BASE_DIR, 'reports')
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, args.output)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {report_path}")

    # 归档到每日报告目录
    archive_path = archive_report(BASE_DIR, f'ETF资金流向_{datetime.now().strftime("%Y%m%d")}.md', report)
    print(f"✅ 报告已归档: {archive_path}")

    progress.complete(f"检测到 {len(signals)} 条信号")

    return monitor

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
            archive_path = archive_report(BASE_DIR, f'综合日报_{datetime.now().strftime("%Y%m%d")}.txt', report_content)

            progress.complete(f"\n✅ 报告已归档到: {archive_path}")

        except Exception as e:
            progress.complete(f"\n❌ 报告生成失败: {e}")
            logger.error(f"报告生成失败: {e}")
    else:
        progress.complete("❌ 每日报告模块不可用")

def run_rebalance(args):
    """再平衡模式 - 执行Excel驱动的再平衡计划 (V4.3增强版)"""
    print("\n🔄 执行Excel驱动再平衡 (V4.3)")
    print("=" * 70)

    progress = ProgressIndicator("再平衡执行", 6)

    # 使用增强版Excel驱动引擎
    progress.update(1, "初始化Excel驱动引擎...")
    strategy_registry = StrategyRegistry()
    engine = ExcelDrivenRebalancingEngineV4(strategy_registry=strategy_registry)

    progress.update(2, "加载5个Excel配置文件...")
    engine.load_all()

    if engine.is_loaded:
        progress.update(3, "构建交易指令...")
        engine.build_trade_orders()

        progress.update(4, "生成报告...")
        report = engine.generate_report()
        print("\n" + report)

        # 注册研究假设
        if strategy_registry:
            strategy_registry.register_hypothesis('rebalance_2024', {
                'title': '2024年组合再平衡',
                'description': '基于Excel配置的12只标的再平衡计划',
                'hypothesis': '核心成长(75%)配置能带来超额收益',
                'status': 'active'
            })
            logger.info("已注册研究假设: rebalance_2024")

        if args.sync_sl:
            progress.update(5, "同步止损止盈规则...")
            engine.sync_to_stop_loss_monitor()
            print("\n✅ 止损止盈规则已同步到 config/rebalance_stop_loss_v43.json")

        if args.output:
            report_dir = os.path.join(BASE_DIR, 'reports')
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, args.output)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n✅ 报告已保存: {report_path}")

        progress.complete("✅ 再平衡执行完成")
    else:
        progress.complete("❌ 无法加载再平衡数据")


def run_monday_rebalance(args):
    """周一调仓自动执行模式 - 读取调仓清单并生成交易指令 (v5.2新增)

    从周一调仓执行清单(MD文件)读取买卖计划，结合实时行情数据，
    自动生成限价单交易指令，支持模拟执行和实盘对接。
    """
    import re
    import json

    print("\n🗓️ 周一调仓自动执行系统 (v5.2)")
    print("=" * 70)

    # 调仓清单路径
    checklist_path = os.path.join(BASE_DIR, '..', '每日报告归档', '交易计划', '周一调仓执行清单.md')

    if not os.path.exists(checklist_path):
        # 尝试备用路径
        alt_paths = [
            os.path.join('..', '..', '每日报告归档', '交易计划', '周一调仓执行清单.md'),
            r'e:\各种PY程序\每日报告归档\交易计划\周一调仓执行清单.md',
        ]
        for p in alt_paths:
            if os.path.exists(p):
                checklist_path = p
                break
        else:
            print("❌ 未找到周一调仓执行清单，请确认文件路径:")
            print(f"   预期路径: {checklist_path}")
            return

    print(f"\n📂 加载调仓清单: {os.path.basename(checklist_path)}")

    # 解析调仓清单
    sell_orders = []   # 卖出指令
    buy_orders = []    # 买入指令
    target_weights = {}  # 目标权重

    with open(checklist_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析买入表格: | # | 标的 | 代码 | 方向 | 股数 | 限价参考 | 预估金额 |
    # MD格式示例: | 1 | **沪深300ETF** | 510300 | 买入 | **48,200股** | 4.985 | ¥240,277 |
    buy_pattern = r'\|\s*(\d+)\s*\|\s*\*{0,2}([^|*]+?)\*{0,2}\s*\|\s*(\d{6})\s*\|\s*(买入|卖出)\s*\|\s*\*{0,2}([\d,]+)股\*{0,2}\s*\|\s*([\d.]+)\s*\|\s*[¥~]?([\d,]+)\s*\|'
    for m in re.finditer(buy_pattern, content):
        idx, name, code, direction, qty_str, price, amount_str = m.groups()
        qty = int(qty_str.replace(',', '').replace('股', '').strip())
        order = {
            'seq': int(idx),
            'name': name.strip(),
            'code': code.strip(),
            'qty': qty,
            'ref_price': float(price),
            'est_amount': round(qty * float(price), 2),
        }
        if direction == '买入':
            buy_orders.append(order)
        else:
            sell_orders.append(order)

    # 解析目标持仓权重
    weight_pattern = r'\|\s*(\d+)\s*\|\s*\*?([^|*]+?)\*?\s*\|\s*(\d{6})\s*\|.*?\|\s*([\d,]+)\s*\|.*?\|\s*\**(\d+)%\*\s*\|'
    for m in re.finditer(weight_pattern, content):
        idx, name, code, _, weight = m.groups()
        target_weights[code.strip()] = {
            'name': name.strip(),
            'weight': int(weight) / 100.0,
        }

    progress = ProgressIndicator("周一调仓执行", 7)

    # === Step 1: 显示卖出计划 ===
    progress.update(1, "解析卖出计划...")
    print(f"\n{'='*60}")
    print(f"  🔴 Step 1 — 卖出计划 ({len(sell_orders)} 笔)")
    print(f"{'='*60}")
    print(f"{'序号':<4} {'标的':<14} {'代码':<8} {'数量':>8} {'参考价':>8} {'预估金额':>10}")
    print(f"{'-'*56}")

    total_sell = 0
    for order in sell_orders:
        print(f"{order['seq']:<4} {order['name']:<14} {order['code']:<8} {order['qty']:>8,} {order['ref_price']:>8.3f} ¥{order['est_amount']:>9,.2f}")
        total_sell += order['est_amount']
    print(f"{'-'*56}")
    print(f"{'合计':<32} {'':>8} ¥{total_sell:>9,.2f}")

    # === Step 2: 显示买入计划 ===
    progress.update(2, "解析买入计划...")
    print(f"\n{'='*60}")
    print(f"  🟢 Step 2 — 买入计划 ({len(buy_orders)} 笔)")
    print(f"{'='*60}")
    print(f"{'序号':<4} {'标的':<14} {'代码':<8} {'数量':>8} {'参考价':>8} {'预估金额':>10}")
    print(f"{'-'*56}")

    total_buy = 0
    for order in buy_orders:
        print(f"{order['seq']:<4} {order['name']:<14} {order['code']:<8} {order['qty']:>8,} {order['ref_price']:>8.3f} ¥{order['est_amount']:>9,.2f}")
        total_buy += order['est_amount']
    print(f"{'-'*56}")
    print(f"{'合计':<32} {'':>8} ¥{total_buy:>9,.2f}")

    # === Step 3: 获取实时行情 (Wind MCP > iFinD > yfinance > 参考价) ===
    progress.update(3, "获取实时行情数据...")
    print(f"\n{'='*60}")
    print(f"  📊 Step 3 — 实时行情对比")
    print(f"{'='*60}")

    all_codes = list(set([o['code'] for o in sell_orders + buy_orders]))
    live_prices = {}

    # --- 数据源1: Wind MCP (并行化) ---
    wind_success = 0
    try:
        skill_dir = r'C:\Users\Administrator\.agents\skills\wind-mcp-skill'

        # 确保Wind API Key传递给子进程
        wind_env = os.environ.copy()
        if not wind_env.get('WIND_API_KEY'):
            wind_env['WIND_API_KEY'] = ''

        def _fetch_one_wind(code):
            """并行获取单只标的Wind行情"""
            if code.startswith(('51', '58')):
                windcode = f"{code}.SH"
            else:
                windcode = f"{code}.SZ"
            try:
                result = subprocess.run(
                    ['node', 'scripts/cli.mjs', 'call', 'fund_data', 'get_fund_quote',
                     _json.dumps({"windcode": windcode})],
                    cwd=skill_dir, capture_output=True, text=True, timeout=15, env=wind_env
                )
                if result.returncode != 0 or not result.stdout.strip():
                    return (code, None)
                data = _json.loads(result.stdout)
                if 'content' in data and len(data['content']) > 0:
                    text = data['content'][0].get('text', '')
                    if text:
                        quote_data = _json.loads(text) if text.startswith('{') else None
                        if quote_data:
                            price = None
                            if 'data' in quote_data and isinstance(quote_data.get('data'), dict):
                                inner = quote_data['data']
                                if 'rows' in inner and isinstance(inner['rows'], list) and len(inner['rows']) > 0:
                                    last_row = inner['rows'][-1]
                                    if isinstance(last_row, list) and len(last_row) >= 2:
                                        p = float(last_row[1])
                                        if p > 0:
                                            price = p
                            if price is None and 'datas' in quote_data and isinstance(quote_data['datas'], list):
                                rows = quote_data['datas']
                                if len(rows) > 0 and isinstance(rows[-1], list) and len(rows[-1]) >= 2:
                                    p = float(rows[-1][1])
                                    if p > 0:
                                        price = p
                            if price is None:
                                for field in ('close', 'last_price', 'price', 'latest_price'):
                                    if field in quote_data:
                                        p = float(quote_data[field])
                                        if p > 0:
                                            price = p
                                            break
                            if price is not None and price > 0:
                                return (code, round(price, 3))
            except Exception:
                pass
            return (code, None)

        with ThreadPoolExecutor(max_workers=min(8, len(all_codes))) as pool:
            futures = {pool.submit(_fetch_one_wind, c): c for c in all_codes}
            for f in as_completed(futures):
                code, price = f.result()
                if price is not None:
                    live_prices[code] = price
                    wind_success += 1

        if wind_success > 0:
            print(f"   Wind MCP: {wind_success}/{len(all_codes)} 只标的行情成功 ✅")
    except Exception as e:
        print(f"   Wind MCP 不可用({e})，尝试下一数据源...")

    # --- 数据源2: iFinD MCP ---
    remaining = [c for c in all_codes if c not in live_prices]
    if remaining:
        ifind_success = 0
        try:
            from hexin_ifind_ds_news_mcp import search_notice  # type: ignore
            # iFinD通过公告MCP间接验证连通性，实际行情走基础接口
            import akshare as ak

            def _fetch_one_akshare(code):
                try:
                    if code.startswith('51') or code.startswith('58'):
                        symbol = f"sh{code}"
                    else:
                        symbol = f"sz{code}"
                    df = ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date="", end_date="", adjust="")
                    if df is not None and not df.empty:
                        price = float(df.iloc[-1]['收盘'])
                        if price > 0:
                            return (code, round(price, 3))
                except Exception:
                    pass
                return (code, None)

            with ThreadPoolExecutor(max_workers=min(8, len(remaining))) as pool:
                futures = {pool.submit(_fetch_one_akshare, c): c for c in remaining}
                for f in as_completed(futures):
                    code, price = f.result()
                    if price is not None:
                        live_prices[code] = price
                        ifind_success += 1

            if ifind_success > 0:
                print(f"   iFinD/akshare: 额外 {ifind_success} 只成功 ✅")
        except ImportError:
            pass
        except Exception as e:
            print(f"   iFinD 不可用({e})")

    # --- 数据源3: yfinance (兜底) ---
    remaining = [c for c in all_codes if c not in live_prices]
    if remaining:
        try:
            import yfinance as yf
            tickers = [f"{c}.SS" if c.startswith(('51', '15')) else f"{c}.SZ"
                       if c.startswith(('00', '30')) else f"{c}.SH"
                       for c in remaining]

            batch_size = 5
            for i in range(0, len(tickers), batch_size):
                batch = tickers[i:i+batch_size]
                data = yf.download(batch, period="1d", progress=False)
                if not data.empty and 'Close' in data.columns:
                    for col in data.columns:
                        code = col.split('.')[0]
                        price = float(data[col]['Close'].iloc[-1])
                        if not np.isnan(price) and price > 0:
                            live_prices[code] = round(price, 3)
        except Exception:
            pass

    # --- 最终兜底: 参考价格 ---
    for o in sell_orders + buy_orders:
        if o['code'] not in live_prices:
            live_prices[o['code']] = o['ref_price']

    total_got = sum(1 for c in all_codes if c in live_prices)
    source_label = "Wind MCP" if wind_success > 0 else ("iFinD" if len(live_prices) > 0 else "参考价格")
    print(f"   行情来源: {source_label} | 覆盖 {total_got}/{len(all_codes)} 只标的")

    # === Step 4: 生成交易指令 ===
    progress.update(4, "生成限价单交易指令...")
    print(f"\n{'='*60}")
    print(f"  📋 Step 4 — 限价单交易指令")
    print(f"{'='*60}")

    # 卖出指令: 参考价 - 0.2% (略微低一点确保成交)
    print(f"\n🔴 卖出限价单 (参考价 × 0.998):")
    print(f"{'代码':<8} {'名称':<12} {'数量':>8} {'参考价':>8} {'限价':>8} {'预估成交':>10}")
    print(f"{'-'*58}")

    trade_instructions = []
    for order in sell_orders:
        code = order['code']
        ref_p = live_prices.get(code, order['ref_price'])
        limit_price = round(ref_p * 0.998, 3)  # 挂低0.2%
        est_fill = round(order['qty'] * limit_price, 2)

        instruction = {
            'action': 'SELL',
            'code': code,
            'name': order['name'],
            'qty': order['qty'],
            'limit_price': limit_price,
            'ref_price': ref_p,
            'est_fill': est_fill,
        }
        trade_instructions.append(instruction)

        print(f"{code:<8} {order['name']:<12} {order['qty']:>8,} {ref_p:>8.3f} {limit_price:>8.3f} ¥{est_fill:>9,.2f}")

    # 买入指令: 参考价 + 0.2% (略微高一点确保成交)
    print(f"\n🟢 买入限价单 (参考价 × 1.002):")
    print(f"{'代码':<8} {'名称':<12} {'数量':>8} {'参考价':>8} {'限价':>8} {'预估成交':>10}")
    print(f"{'-'*58}")

    for order in buy_orders:
        code = order['code']
        ref_p = live_prices.get(code, order['ref_price'])
        limit_price = round(ref_p * 1.002, 3)  # 挂高0.2%
        est_fill = round(order['qty'] * limit_price, 2)

        instruction = {
            'action': 'BUY',
            'code': code,
            'name': order['name'],
            'qty': order['qty'],
            'limit_price': limit_price,
            'ref_price': ref_p,
            'est_fill': est_fill,
        }
        trade_instructions.append(instruction)

        print(f"{code:<8} {order['name']:<12} {order['qty']:>8,} {ref_p:>8.3f} {limit_price:>8.3f} ¥{est_fill:>9,.2f}")

    # === Step 5: 调仓后持仓预览 ===
    progress.update(5, "计算调仓后持仓...")
    print(f"\n{'='*60}")
    print(f"  ✅ Step 5 — 调仓后目标持仓")
    print(f"{'='*60}")

    total_sell_est = sum([t['est_fill'] for t in trade_instructions if t['action'] == 'SELL'])
    total_buy_est = sum([t['est_fill'] for t in trade_instructions if t['action'] == 'BUY'])
    net_cash = total_sell_est - total_buy_est

    print(f"   卖出回收:     ¥{total_sell_est:>12,.2f}")
    print(f"   买入支出:     ¥{total_buy_est:>12,.2f}")
    print(f"   净现金流:      {'¥'+str(round(net_cash, 2)) if net_cash >= 0 else '-¥'+str(abs(round(net_cash, 2))):>13}")
    print(f"   手续费估算:   ¥{round((total_sell_est + total_buy_est) * 0.0003, 2):>12,.2f} (万三)")

    # === Step 6: 风控检查 ===
    progress.update(6, "风控纪律检查...")
    print(f"\n{'='*60}")
    print(f"  🔐 Step 6 — 三级风控纪律")
    print(f"{'='*60}")
    print(f"""
┌──────────────────────────────────────────────┐
│  🟢 浮亏 ≥ -8%   → 预警冻结，逐标检视       │
│  🟡 浮亏 ≥ -12%  → 减仓，权益降至60%         │
│  🔴 浮亏 ≥ -15%  → 强制避险，权益降至40%       │
│                                              │
│  ⏰ 下次调仓检查: 下周一                     │
│  📱 止损监控命令: python ... --risk           │
└──────────────────────────────────────────────┘
""")

    # === 保存交易指令文件 ===
    progress.complete("✅ 周一调仓执行准备完成")

    # 保存为JSON供后续使用
    output_data = {
        'execution_date': datetime.now().strftime('%Y-%m-%d'),
        'sell_orders': sell_orders,
        'buy_orders': buy_orders,
        'trade_instructions': trade_instructions,
        'live_prices': live_prices,
        'total_sell_est': total_sell_est,
        'total_buy_est': total_buy_est,
        'net_cash': round(net_cash, 2),
        'target_weights': target_weights,
        'risk_rules': {
            'warning_pct': -0.08,
            'reduce_pct': -0.12,
            'force_safe_pct': -0.15,
        },
    }

    # 保存交易指令
    report_dir = os.path.join(BASE_DIR, 'reports')
    os.makedirs(report_dir, exist_ok=True)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = os.path.join(report_dir, f'monday_rebalance_{ts}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)

    # 保存可读的交易指令清单
    md_path = os.path.join(report_dir, f'monday_rebalance_{ts}.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# 🗓️ 周一调仓交易指令\n\n")
        f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"> 数据来源: 周一调仓执行清单.md\n\n")
        f.write(f"---\n\n")
        f.write(f"## 🔴 卖出指令 ({len(sell_orders)} 笔)\n\n")
        f.write(f"| 代码 | 名称 | 数量 | 参考价 | **限价** | 预估成交 |\n")
        f.write(f"|------|------|:----:|--------:|--------:|----------:|\n")
        for t in trade_instructions:
            if t['action'] == 'SELL':
                f.write(f"| {t['code']} | {t['name']} | {t['qty']:,} | {t['ref_price']} | **{t['limit_price']}** | ¥{t['est_fill']:,.2f} |\n")
        f.write(f"\n**卖出合计**: ¥{total_sell_est:,.2f}\n\n")
        f.write(f"## 🟢 买入指令 ({len(buy_orders)} 笔)\n\n")
        f.write(f"| 代码 | 名称 | 数量 | 参考价 | **限价** | 预估成交 |\n")
        f.write(f"|------|------|:----:|--------:|--------:|----------:|\n")
        for t in trade_instructions:
            if t['action'] == 'BUY':
                f.write(f"| {t['code']} | {t['name']} | {t['qty']:,} | {t['ref_price']} | **{t['limit_price']}** | ¥{t['est_fill']:,.2f} |\n")
        f.write(f"\n**买入合计**: ¥{total_buy_est:,.2f}\n\n")
        f.write(f"## 💰 资金汇总\n\n")
        f.write(f"| 项目 | 金额 |\n|------|--------:|\n")
        f.write(f"| 卖出回收 | ¥{total_sell_est:,.2f} |\n")
        f.write(f"| 买入支出 | ¥{total_buy_est:,.2f} |\n")
        f.write(f"| 净现金流 | {'+' if net_cash >= 0 else ''}¥{abs(net_cash):,.2f} |\n")
        f.write(f"| 手续费(≈万3) | ¥{round((total_sell_est+total_buy_est)*0.0003, 2):,.2f} |\n")
        f.write(f"\n## 🔐 风控纪律\n\n")
        f.write(f"- 🟢 浮亏 ≥ **-8%** → 预警冻结\n")
        f.write(f"- 🟡 浮亏 ≥ **-12%** → 减仓至60%\n")
        f.write(f"- 🔴 浮亏 ≥ **-15%** → 强制避险至40%\n")

    print(f"\n📁 交易指令已保存:")
    print(f"   JSON: {json_path}")
    print(f"   Markdown: {md_path}")

    return output_data


def run_backtest(args):
    """回测模式 - 历史数据回测验证"""
    print("\n📊 运行回测")
    print("=" * 70)

    progress = ProgressIndicator("回测执行", 4)

    progress.update(1, "加载回测模块(v2增强版)...")
    try:
        from fast_backtest_v2 import run_fast_backtest
        progress.update(2, "执行快速回测(v2)...")
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
        quotes = {}
        get_quotes_batch = data_provider.get('get_quotes_batch')
        if get_quotes_batch:
            config = load_portfolio_config()
            if config:
                codes = [a['code'] for a in config.get('assets', [])]
                # ETF: 5xxxxx (上交所) / 159915等 (深交所)
                stocks = [c for c in codes if not (c.startswith('5') or c == '159915')]
                funds = [c for c in codes if c.startswith('5') or c == '159915']
                prices = get_quotes_batch(stocks, funds)
                quotes = {k: {'price': v['price']} for k, v in prices.items() if v['price'] > 0}

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


def run_quick_check(args):
    """快速检查模式 - 检查系统状态"""
    print("\n🔍 系统状态快速检查")
    print("=" * 70)

    # 检查模块可用性
    modules = {
        '数据提供层': data_provider.get('get_quotes_batch') is not None,
        '自动交易系统': auto_trading.get('AutoTradingSystem') is not None,
        '再平衡引擎': rebalance_engine.get('RebalancingEngine') is not None,
        '每日报告': daily_report.get('generate_daily_report') is not None,
        '止损止盈监控': stop_loss.get('StopLossMonitor') is not None,
        '策略注册表': strategy_registry is not None,
        '连接器管理器': connector_manager is not None,
        'ETF资金流向监控': True,  # 内置模块，始终可用
        '投资组合优化': PortfolioOptimizationEngine().pd is not None,  # 新增
        '康波周期监控': KommoCommodityMonitor().yf_available or KommoCommodityMonitor().ts_available,  # 新增
        '大宗商品基本面': _check_commodity_module(),  # 动态检查
        '时序预测模型': all(__import__(pkg) for pkg in ['torch', 'sklearn', 'pandas', 'numpy'] if __import__('importlib').util.find_spec(pkg)),  # 新增
        '配置管理器': config_manager is not None,
        '优雅降级管理器': graceful_fallback is not None,
        '康波周期分析(v5.1)': KONDRATIEV_AVAILABLE,  # v5.1新增
        '十五五规划分析(v5.1)': FIFTEEN_FIVE_AVAILABLE,  # v5.1新增
        '社保基金ETF追踪(v5.1)': SOCIAL_SECURITY_ETF_AVAILABLE,  # v5.1新增
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

    # 保存报告
    if args.output:
        report_dir = os.path.join(BASE_DIR, 'reports')
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, args.output)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {report_path}")

    # 归档到每日报告目录
    archive_path = archive_report(BASE_DIR, f'投资组合优化_{datetime.now().strftime("%Y%m%d")}.txt', report)
    print(f"✅ 报告已归档: {archive_path}")

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

    # 保存报告
    if args.output:
        report_dir = os.path.join(BASE_DIR, 'reports')
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, args.output)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {report_path}")

    # 归档到每日报告目录
    archive_path = archive_report(BASE_DIR, f'康波周期监控_{datetime.now().strftime("%Y%m%d")}.md', report)
    print(f"✅ 报告已归档: {archive_path}")

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

        progress.update(2, "获取铜、金、银等大宗商品数据...")
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
            report_lines.append(f"- **{k}**: {v}")

        report_lines.extend([
            "",
            "---",
            "*本报告由大宗商品基本面分析模块自动生成*",
        ])

        report = "\n".join(report_lines)
        print("\n" + report)

        # 保存报告
        if args.output:
            report_dir = os.path.join(BASE_DIR, 'reports')
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, args.output)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n✅ 报告已保存: {report_path}")

        # 归档到每日报告目录
        archive_path = archive_report(BASE_DIR, f'大宗商品基本面_{datetime.now().strftime("%Y%m%d")}.md', report)
        print(f"✅ 报告已归档: {archive_path}")

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

    # 保存报告
    if args.output:
        report_path = os.path.join(BASE_DIR, 'reports', args.output)
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {report_path}")

    archive_path = archive_report(BASE_DIR, f'康波周期分析_{datetime.now().strftime("%Y%m%d")}.md', report)
    print(f"✅ 报告已归档: {archive_path}")

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

    # 保存报告
    if args.output:
        report_path = os.path.join(BASE_DIR, 'reports', args.output)
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {report_path}")

    archive_path = archive_report(BASE_DIR, f'十五五规划适配_{datetime.now().strftime("%Y%m%d")}.md', report)
    print(f"✅ 报告已归档: {archive_path}")

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
        if flow_monitor.flow_data:
            # 转换为 SocialSecurityETFTracker 需要的格式
            flow_data = {}
            for code, data in flow_monitor.flow_data.items():
                flow_data[code] = {
                    "name": data.get("name", code),
                    "net_flow_yi": data.get("net_flow_yi", 0),
                    "trend": data.get("trend", "中性"),
                    "category": data.get("category", "未知"),
                }
            print(f"\n  💰 已获取 {len(flow_data)} 只ETF资金流数据")
    except Exception as e:
        logger.debug(f"获取ETF资金流数据失败（将使用静态分析）: {e}")

    report = tracker.generate_report(flow_data=flow_data)

    # 保存报告
    if args.output:
        report_path = os.path.join(BASE_DIR, 'reports', args.output)
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {report_path}")

    archive_path = archive_report(BASE_DIR, f'社保基金ETF追踪_{datetime.now().strftime("%Y%m%d")}.md', report)
    print(f"✅ 报告已归档: {archive_path}")

    progress.complete("✅ 社保基金ETF追踪完成")
    return tracker


def run_macro_analysis(args):
    """宏观综合分析 — 一键运行康波周期 + 十五五规划 + 社保基金ETF三大分析"""
    print("\n🔬 宏观综合分析（康波周期 + 十五五规划 + 社保基金ETF）")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)

    archive_dir = get_archive_dir(BASE_DIR)

    # ── 并行运行三大独立分析模块 ──
    def _run_kondratiev():
        """康波周期分析 (独立模块)"""
        if not KONDRATIEV_AVAILABLE:
            return ('kondratiev', None)
        try:
            kondratiev = KondratievCycleAnalyzer()
            phase = kondratiev.get_current_phase()
            lines = []
            lines.append(f"\n  📍 第六轮康波（AI/算力驱动）当前阶段: {phase['phase_name_cn']}")
            lines.append(f"  📊 阶段进度: {phase['progress_pct']}% | 置信度: {phase['confidence']}")
            lines.append(f"  🎯 推荐风格: {phase['recommended_style']} | 风险等级: {phase['risk_level']}")
            lines.append(f"  🔄 预计转入下一阶段: {phase['estimated_transition']}")
            lines.append(f"\n  📈 康波周期行业配置建议:")
            for s in kondratiev.get_sector_allocation():
                lines.append(f"    {s['sector']}: 综合得分={s['combined_score']} → {s['recommendation']}")
            lines.append(f"\n  🛢️ 大宗商品周期信号:")
            for c in kondratiev.get_commodity_signals():
                lines.append(f"    {c['name']}: 信号={c['current_signal']}, 康波建议={c['kondratiev_recommendation']}")
            overlay = kondratiev.get_fifteen_five_overlay()
            lines.append(f"\n  🔗 十五五与康波交叠结论:")
            lines.append(f"    {overlay['synergy_conclusion'][:100]}...")
            report = kondratiev.generate_report()
            archive_report(BASE_DIR, f'康波周期分析_{datetime.now().strftime("%Y%m%d")}.md', report)
            lines.append(f"\n  ✅ 康波周期报告已归档")
            return ('kondratiev', True, '\n'.join(lines))
        except Exception as e:
            return ('kondratiev', False, f"\n  ❌ 康波周期分析失败: {e}")

    def _run_fifteen_five():
        """十五五规划分析 (独立模块)"""
        if not FIFTEEN_FIVE_AVAILABLE:
            return ('fifteen_five', None)
        try:
            fifteen_five = FifteenFivePlanAnalyzer()
            holdings = fifteen_five.analyze_holdings()
            adjustments = fifteen_five.get_weight_adjustments()
            lines = []
            lines.append(f"\n  📊 持仓十五五适配评级:")
            for h in holdings:
                flag = "🟢" if h['overall_score'] >= 85 else "🟡" if h['overall_score'] >= 70 else "🔴"
                lines.append(f"    {flag} {h['name']}: 评分={h['overall_score']}, 等级={h['grade']}")
            lines.append(f"\n  ⚖️ 十五五驱动的权重调整建议:")
            for adj in adjustments:
                if adj['weight_adjust_pct'] != 0:
                    direction = "▲" if adj['weight_adjust_pct'] > 0 else "▼"
                    lines.append(f"    {direction} {adj['name']}: {adj['suggestion']} ({adj['weight_adjust_pct']:+.1f}%)")
            report = fifteen_five.generate_report()
            archive_report(BASE_DIR, f'十五五规划适配_{datetime.now().strftime("%Y%m%d")}.md', report)
            lines.append(f"\n  ✅ 十五五规划报告已归档")
            return ('fifteen_five', True, '\n'.join(lines))
        except Exception as e:
            return ('fifteen_five', False, f"\n  ❌ 十五五规划分析失败: {e}")

    def _run_social_security():
        """社保基金ETF追踪 (独立模块)"""
        if not SOCIAL_SECURITY_ETF_AVAILABLE:
            return ('social_security', None)
        try:
            ss_tracker = SocialSecurityETFTracker()
            summary = ss_tracker.classifier.get_style_summary()
            lines = []
            lines.append(f"\n  📊 社保基金四大投资风格:")
            for style, info in summary.items():
                icon = "📈" if info['recommended_action'] == "超配" else "📊" if info['recommended_action'] == "标配" else "📉"
                lines.append(f"    {icon} {style} ({info['weight']:.0%}): {info['recommended_action']}")
                lines.append(f"       代表ETF: {', '.join(info['top_etfs'][:2])}")

            flow_data = None
            try:
                flow_monitor = ETFFundFlowMonitor(data_connector_manager=connector_manager)
                flow_monitor.analyze_fund_flow()
                if flow_monitor.flow_data:
                    flow_data = {}
                    for code, data in flow_monitor.flow_data.items():
                        flow_data[code] = {
                            "name": data.get("name", code),
                            "net_flow_yi": data.get("net_flow_yi", 0),
                            "trend": data.get("trend", "中性"),
                            "category": data.get("category", "未知"),
                        }
            except Exception:
                pass

            report = ss_tracker.generate_report(flow_data=flow_data)
            archive_report(BASE_DIR, f'社保基金ETF追踪_{datetime.now().strftime("%Y%m%d")}.md', report)
            lines.append(f"\n  ✅ 社保基金ETF报告已归档")
            return ('social_security', True, '\n'.join(lines))
        except Exception as e:
            return ('social_security', False, f"\n  ❌ 社保基金ETF追踪失败: {e}")

    # 并行执行
    results = {}
    section_titles = {
        'kondratiev': "第一部分：康波周期 + 十五五规划交叠分析",
        'fifteen_five': "第二部分：十五五规划适配分析",
        'social_security': "第三部分：社保基金ETF风格追踪",
    }
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(fn): fn.__name__
            for fn in [_run_kondratiev, _run_fifteen_five, _run_social_security]
        }
        for f in as_completed(futures):
            key, status, *extra = f.result()
            results[key] = status
            if status is None:
                print(f"\n  ⚠️ {section_titles.get(key, key)}模块不可用，跳过")
            else:
                print("\n" + "=" * 50)
                print(f"  {section_titles.get(key, key)}")
                print("=" * 50)
                if extra:
                    print(extra[0])

    # 汇总
    print("\n" + "=" * 70)
    success_count = sum(1 for v in results.values() if v is True)
    total_count = sum(1 for v in results.values() if v is not None)
    print(f"🔬 宏观综合分析完成: {success_count}/{total_count} 模块成功")
    print(f"📁 报告归档目录: {archive_dir}")
    print("=" * 70)

    return results


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
# v5.2新增: engine.etf_flow + engine.social_security 独立运行模式
# ============================================================

def run_etf_flow_v2(args):
    """实时ETF资金流监控 — 使用 engine.etf_flow 模块"""
    print("\n🌊 实时ETF资金流向监控 (v5.2)")
    print("=" * 70)

    if not ETF_FLOW_AVAILABLE or ETFRealTimeTracker is None:
        print("❌ engine.etf_flow 模块不可用")
        return

    tracker = ETFRealTimeTracker()
    print(f"  监控标的: {len(tracker.etf_list)} 只ETF")
    print("  数据源优先级: Wind MCP > tushare > yfinance > 模拟数据")
    print()

    flows = tracker.analyze_fund_flow()
    signals = tracker.detect_signals(flows)
    report = tracker.generate_report(signals, flows)

    print(f"\n✅ 分析完成: {len(flows)} 只ETF, {len(signals)} 条信号")
    print()
    print(report)

    if getattr(args, 'output', None):
        out_path = os.path.join(BASE_DIR, 'reports', args.output)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {out_path}")


def run_social_security_v2(args):
    """社保基金ETF风格追踪 — 使用 engine.social_security 模块"""
    print("\n🏦 社保基金ETF风格追踪 (v5.2)")
    print("=" * 70)

    if not SOCIAL_SECURITY_V2_AVAILABLE:
        print("❌ engine.social_security 模块不可用")
        return

    # 1) 先运行 ETF 资金流做前置输入
    flow_data = None
    if ETF_FLOW_AVAILABLE and ETFRealTimeTracker is not None:
        tracker = ETFRealTimeTracker()
        flow_data = tracker.analyze_fund_flow()
        print(f"  [前置] ETF资金流分析完成: {len(flow_data)} 只标的")

    # 2) 读取持仓
    holdings = None
    positions_path = os.path.join(BASE_DIR, 'config', 'positions.json')
    if os.path.exists(positions_path):
        try:
            with open(positions_path, 'r', encoding='utf-8') as f:
                positions = json.load(f)
                cash = float(positions.get('cash', 0))
                holdings = {
                    "核心资产": cash * 0.25,
                    "周期/顺周期": cash * 0.20,
                    "防御/红利": cash * 0.25,
                    "成长科技": cash * 0.15,
                    "金融/银行": cash * 0.15,
                }
                print(f"  [持仓] 已从 positions.json 加载 (现金 ￥{cash:,.0f})")
        except Exception as e:
            logger.warning(f"读取持仓失败: {e}")

    # 3) 运行主追踪器
    result = _ss_run(flow_data, holdings)
    print()
    print(result["report"])

    if getattr(args, 'output', None):
        out_path = os.path.join(BASE_DIR, 'reports', args.output)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(result["report"])
        print(f"\n✅ 报告已保存: {out_path}")


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='量化策略系统 v5.1 — 康波周期 + 十五五规划 + 社保基金ETF追踪',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='\n'.join([
            '架构: Connector-first多数据源 | 策略注册表 | 假设验证 | 投资组合优化',
            '新增(v5.1): 康波周期+十五五交叠分析 | 社保基金ETF风格追踪 | 宏观综合分析',
        ])
    )

    # 运行模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--daily', action='store_true', help='三阶段交易工作流 (盘前计划/盘中策略/盘后报告)')
    mode_group.add_argument('--live', action='store_true', help='实时监控模式')
    mode_group.add_argument('--report', action='store_true', help='报告生成模式')
    mode_group.add_argument('--rebalance', action='store_true', help='再平衡模式')
    mode_group.add_argument('--backtest', action='store_true', help='回测模式')
    mode_group.add_argument('--risk', action='store_true', help='风险监控模式')
    mode_group.add_argument('--check', action='store_true', help='快速检查模式')
    mode_group.add_argument('--hypothesis', action='store_true', help='假设验证模式')
    mode_group.add_argument('--etf-flow', action='store_true', help='ETF资金流向监控模式')
    mode_group.add_argument('--portfolio-opt', action='store_true', help='投资组合优化模式 (新增)')
    mode_group.add_argument('--kommo-monitor', action='store_true', help='康波周期监控模式 (新增)')
    mode_group.add_argument('--commodity-fund', action='store_true', help='大宗商品基本面分析模式 (新增)')
    mode_group.add_argument('--train-model', action='store_true', help='时序预测模型训练模式 (新增)')
    mode_group.add_argument('--kondratiev', action='store_true', help='康波周期+十五五交叠分析模式 (v5.1新增)')
    mode_group.add_argument('--fifteen-five', action='store_true', help='十五五规划适配分析模式 (v5.1新增)')
    mode_group.add_argument('--social-security', action='store_true', help='社保基金ETF风格追踪模式 (v5.1新增)')
    mode_group.add_argument('--macro-analysis', action='store_true', help='宏观综合分析（康波+十五五+社保ETF一键运行）(v5.1新增)')
    mode_group.add_argument('--monday-rebalance', action='store_true', help='周一调仓自动执行 - 读取调仓清单+实时行情+生成限价单指令 (v5.2新增)')
    mode_group.add_argument('--etf-flow-v2', action='store_true', help='实时ETF资金流向监控 (engine.etf_flow 模块) (v5.2新增)')
    mode_group.add_argument('--social-security-v2', action='store_true', help='社保基金ETF风格追踪 (engine.social_security 模块) (v5.2新增)')

    # --daily 子阶段
    parser.add_argument('--phase', choices=['premarket', 'intraday', 'postmarket', 'all'],
                        default='all', help='三阶段工作流子阶段 (配合 --daily 使用)')

    # 通用选项
    parser.add_argument('--no-ai', action='store_true', help='禁用AI分析模块')
    parser.add_argument('--output', '-o', default=None, help='输出报告文件名')
    parser.add_argument('--sync-sl', action='store_true', help='同步止损止盈规则')

    # 假设验证选项
    parser.add_argument('--list', action='store_true', help='列出研究假设')
    parser.add_argument('--register', type=str, help='注册新假设: id|名称|描述')
    parser.add_argument('--validate', type=str, help='验证指定假设')

    args = parser.parse_args()

    # 模式调度表 — 映射arg名称到处理函数
    MODE_DISPATCH = {
        'daily': run_daily_workflow,
        'live': run_live_monitoring,
        'report': run_report_generation,
        'rebalance': run_rebalance,
        'backtest': run_backtest,
        'risk': run_risk_monitor,
        'check': run_quick_check,
        'hypothesis': run_hypothesis_test,
        'etf_flow': run_etf_flow_monitor,
        'portfolio_opt': run_portfolio_optimization,
        'kommo_monitor': run_kommo_monitor,
        'commodity_fund': run_commodity_fundamentals,
        'train_model': run_model_training,
        'kondratiev': run_kondratiev_analysis,
        'fifteen_five': run_fifteen_five_analysis,
        'social_security': run_social_security_analysis,
        'macro_analysis': run_macro_analysis,
        'monday_rebalance': run_monday_rebalance,
        'etf_flow_v2': run_etf_flow_v2,
        'social_security_v2': run_social_security_v2,
    }

    for mode_name, handler in MODE_DISPATCH.items():
        if getattr(args, mode_name, False):
            handler(args)
            break

if __name__ == '__main__':
    # 打印启动信息
    print("=" * 70)
    print("          量化策略系统 v5.1 — 运行模式调度")
    print("                    HKUDS/Vibe-Trading Architecture")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)

    main()
