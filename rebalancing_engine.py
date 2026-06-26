# -*- coding: utf-8 -*-
"""
再平衡引擎 — 将多维度调仓数据统一纳入量化策略系统

数据源 (6份Excel):
  1. batch_execution_plan        → 分批执行计划 (时间线)
  2. complete_rebalancing_plan   → 完整再平衡方案 (仓位/止损/止盈)
  3. execution_summary_and_tips  → 执行摘要与风控要点
  4. fund_flow_summary           → 资金流向汇总
  5. portfolio_comparison_analysis → 调仓前后对比分析

功能:
  - 加载并校验所有Excel数据源
  - 生成可执行的交易指令清单 (按批次)
  - 计算资金需求与回笼预估
  - 与止损止盈监控联动 (动态更新规则)
  - 输出标准化再平衡报告
  - 集成到每日报告 / 定时任务

使用方式:
  from rebalancing_engine import RebalancingEngine

  engine = RebalancingEngine('config/rebalance_data/')
  engine.load_all()
  report = engine.generate_report()
  trades = engine.get_pending_trades()       # 待执行交易
  sl_rules = engine.export_sl_tp_rules()     # 导出止损止盈规则
"""

import os
import json
import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field

import pandas as pd
import yaml
import numpy as np

warnings.filterwarnings('ignore')

_log = logging.getLogger('rebalance')
_log.setLevel(logging.INFO)
if not _log.handlers:
    _fh = logging.FileHandler(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs',
                     f'rebalance_{datetime.now():%Y%m%d}.log'),
        encoding='utf-8'
    )
    _fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    _log.addHandler(_fh)


class BatchPhase(Enum):
    """执行批次"""
    PHASE_1 = "第一批"      # 本周内 (高优先级: 清仓极度高估 + 减持高估值)
    PHASE_2 = "第二批"      # 1个月内 (核心调仓: 减持/增持/维持)
    PHASE_3 = "第三批"      # 3个月内 (防御增强: 黄金ETF + 沪深300ETF)


class TradeAction(Enum):
    CLEAR = "清仓"          # 全部卖出
    REDUCE = "减持"         # 部分卖出
    INCREASE = "增持"       # 加仓
    HOLD = "维持"           # 不变
    NEW = "新增"            # 新建仓


@dataclass
class TradeOrder:
    """单笔交易指令"""
    code: str
    name: str
    action: TradeAction
    phase: BatchPhase
    target_shares: int          # 目标持仓股数 (含符号, 正=买/负=卖)
    price: float               # 参考价格 (元)
    estimated_amount: float     # 预计金额 (元)
    direction: str              # "买入"/"卖出"
    fund_flow: str             # "流入"/"流出"
    deadline: str               # 执行期限
    notes: str                 # 操作说明
    priority: str = "中"        # 高/中/低
    executed: bool = False
    executed_at: Optional[str] = None
    actual_price: Optional[float] = None
    actual_amount: Optional[float] = None


@dataclass
class FundFlowSummary:
    """资金流向汇总"""
    sell_total: float = 0.0            # 卖出合计
    buy_total: float = 0.0             # 买入合计
    net_flow: float = 0.0              # 净流动 (正=流入/负=流出)
    additional_capital: float = 0.0    # 需追加资金
    transaction_fee: float = 0.0       # 交易费用
    details_sell: List[Dict] = field(default_factory=list)
    details_buy: List[Dict] = field(default_factory=list)


@dataclass
class PortfolioComparison:
    """组合对比指标"""
    metrics_before: Dict[str, Any]
    metrics_after: Dict[str, Any]
    improvements: List[str]


# ---- 数据文件名映射 ----
DATA_FILES = {
    'batch_plan': 'data_extraction_batch_execution_plan - 副本.xlsx',
    'full_plan': 'data_extraction_complete_rebalancing_plan - 副本.xlsx',
    'summary': 'data_extraction_execution_summary_and_tips.xlsx',   # 优先用非副本
    'fund_flow': 'data_extraction_fund_flow_summary.xlsx',
    'comparison': 'data_extraction_portfolio_comparison_analysis - 副本.xlsx',
}


class RebalancingEngine:
    """
    再平衡引擎核心类。

    统一管理6份Excel数据源，提供:
      - 数据加载与交叉校验
      - 交易指令生成 (按优先级排序)
      - 资金流计算
      - 止损止盈规则导出
      - 报告生成
      - 执行状态追踪
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        Args:
            data_dir: Excel数据所在目录，默认为模块同目录
        """
        if data_dir is None:
            data_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = data_dir

        # 原始数据
        self._batch_df: Optional[pd.DataFrame] = None
        self._full_plan_df: Optional[pd.DataFrame] = None
        self._summary_df: Optional[pd.DataFrame] = None
        self._fund_flow_df: Optional[pd.DataFrame] = None
        self._comparison_df: Optional[pd.DataFrame] = None

        # 处理后结果
        self.trade_orders: List[TradeOrder] = []
        self.fund_flow: FundFlowSummary = FundFlowSummary()
        self.comparison: Optional[PortfolioComparison] = None
        self.sl_tp_rules: Dict[str, Dict] = {}       # {code: {stop_loss, take_profit, ...}}

        # 元信息
        self.loaded_at: Optional[str] = None
        self.load_errors: List[str] = []
        self.validation_warnings: List[str] = []

    def load_all(self) -> bool:
        """加载所有6份数据源。返回是否全部成功。"""
        self.load_errors = []
        base = self.data_dir

        # 1. 批次执行计划
        self._batch_df = self._load_excel(
            os.path.join(base, DATA_FILES['batch_plan']), 'batch_plan')
        # 2. 完整再平衡方案
        self._full_plan_df = self._load_excel(
            os.path.join(base, DATA_FILES['full_plan']), 'full_plan')
        # 3. 执行摘要 (优先非副本)
        fp_summary = os.path.join(base, DATA_FILES['summary'])
        if not os.path.exists(fp_summary):
            fp_summary = os.path.join(base,
                                      'data_extraction_execution_summary_and_tips - 副本.xlsx')
        self._summary_df = self._load_excel(fp_summary, 'summary')
        # 4. 资金流向
        self._fund_flow_df = self._load_excel(
            os.path.join(base, DATA_FILES['fund_flow']), 'fund_flow')
        # 5. 对比分析
        self._comparison_df = self._load_excel(
            os.path.join(base, DATA_FILES['comparison']), 'comparison')

        self.loaded_at = datetime.now().isoformat()

        if not self.load_errors:
            self._post_load_process()
            _log.info("全部数据源加载完成: %s", self.loaded_at)
        else:
            _log.warning("部分数据源加载失败: %s", self.load_errors)

        return len(self.load_errors) == 0

    # ---- 数据访问 ----

    @property
    def is_loaded(self) -> bool:
        return self._full_plan_df is not None and len(self._full_plan_df) > 0

    @property
    def total_assets(self) -> int:
        if self._full_plan_df is None:
            return 0
        return len(self._full_plan_df)

    def get_full_plan(self) -> pd.DataFrame:
        """返回完整再平衡方案的DataFrame副本"""
        return self._full_plan_df.copy() if self._full_plan_df is not None else pd.DataFrame()

    def get_batch_plan(self) -> pd.DataFrame:
        """返回批次执行计划的DataFrame副本"""
        return self._batch_df.copy() if self._batch_df is not None else pd.DataFrame()

    def get_asset_detail(self, code: str) -> Optional[Dict]:
        """查询单个标的的完整调仓信息"""
        if self._full_plan_df is None:
            return None
        col_code = self._find_col(self._full_plan_df, ['证券代码', 'code'])
        if col_code is None:
            return None
        mask = self._full_plan_df[col_code].astype(str).str.contains(
            str(code).zfill(6), na=False)
        row = self._full_plan_df[mask]
        if row.empty:
            return None
        r = row.iloc[0]
        return r.to_dict()

    # ---- 交易指令 ----

    def build_trade_orders(self, current_prices: Optional[Dict[str, float]] = None
                           ) -> List[TradeOrder]:
        """
        从批次执行计划构建完整的交易指令列表。

        Args:
            current_prices: 当前实时行情 {code: price}，用于更新参考价。
                            为None时使用Excel中的最新价。

        Returns:
            按 (phase优先级, code) 排序的交易指令列表
        """
        if self._batch_df is None or self._batch_df.empty:
            _log.warning("无批次执行计划数据")
            return []

        orders = []
        col_map = self._resolve_cols(self._batch_df, {
            'batch': ['批次'],
            'time': ['执行时间'],
            'code': ['证券代码'],
            'name': ['证券名称'],
            'action': ['操作类型'],
            'shares': ['需调整股数'],
            'amount': ['预计交易金额(元)'],
            'flow': ['资金流向'],
            'cumulative': ['累计资金变化(元)'],
            'notes': ['操作说明'],
        })
        # Build column position map for fast itertuples() access
        col_idx = {}
        for key, col_name in col_map.items():
            if col_name in self._batch_df.columns:
                col_idx[key] = self._batch_df.columns.get_loc(col_name)

        for row in self._batch_df.itertuples(index=False):
            raw_code = str(row[col_idx.get('code', 0)]).strip()
            code = self._normalize_code(raw_code)
            name = str(row[col_idx.get('name', 1)])
            action_str = str(row[col_idx.get('action', 2)] or '维持').strip()
            shares = self._safe_int(row[col_idx.get('shares', 3)])
            amount = self._safe_float(row[col_idx.get('amount', 4)])
            flow = str(row[col_idx.get('flow', 5)] or '')
            cumulative = self._safe_float(row[col_idx.get('cumulative', 6)])
            notes = str(row[col_idx.get('notes', 7)] or '')
            batch_str = str(row[col_idx.get('batch', 8)] or '第二批').strip()
            deadline = str(row[col_idx.get('time', 9)] or '')

            phase = self._parse_phase(batch_str)
            action = self._parse_action(action_str)
            direction = "买入" if shares > 0 else "卖出"
            priority = self._calc_priority(action, phase)

            # 参考价
            ref_price = amount / abs(shares) if shares != 0 else 0
            if current_prices and code in current_prices:
                ref_price = current_prices[code]

            order = TradeOrder(
                code=code, name=name, action=action, phase=phase,
                target_shares=shares, price=round(ref_price, 2),
                estimated_amount=round(amount, 2),
                direction=direction, fund_flow=flow,
                deadline=deadline, notes=notes,
                priority=priority
            )
            orders.append(order)

        # 排序: 优先卖出再买入; 同方向内按批次+动作优先级
        # ⭐ 先卖出(回笼资金) → 再买入(使用已回笼资金)
        phase_order = {BatchPhase.PHASE_1: 0, BatchPhase.PHASE_2: 1, BatchPhase.PHASE_3: 2}
        action_order = {TradeAction.CLEAR: 0, TradeAction.REDUCE: 1,
                        TradeAction.INCREASE: 2, TradeAction.NEW: 3, TradeAction.HOLD: 4}
        direction_order = {"卖出": 0, "买入": 1}
        orders.sort(key=lambda o: (
            direction_order.get(o.direction, 99),
            phase_order.get(o.phase, 99),
            action_order.get(o.action, 99)
        ))
        self.trade_orders = orders
        return orders

    def get_pending_trades(self) -> List[TradeOrder]:
        """获取未执行的交易指令"""
        return [o for o in self.trade_orders if not o.executed]

    def get_trades_by_phase(self, phase: BatchPhase) -> List[TradeOrder]:
        """按批次筛选"""
        return [o for o in self.trade_orders if o.phase == phase]

    def mark_executed(self, code: str, actual_price: float,
                      actual_amount: float) -> bool:
        """标记某笔交易为已执行"""
        for o in self.trade_orders:
            if o.code == code and not o.executed:
                o.executed = True
                o.executed_at = datetime.now().isoformat()
                o.actual_price = actual_price
                o.actual_amount = actual_amount
                _log.info("[EXECUTED] %s %s price=%.2f amount=%.2f",
                          code, o.name, actual_price, actual_amount)
                return True
        return False

    # ---- 资金流向 ----

    def calculate_fund_flow(self) -> FundFlowSummary:
        """从fund_flow_summary数据计算资金流向"""
        fs = FundFlowSummary()
        if self._fund_flow_df is None or self._fund_flow_df.empty:
            return fs

        col_map = self._resolve_cols(self._fund_flow_df, {
            'item': ['项目'], 'amount': ['金额(元)'], 'desc': ['说明']
        })
        col_idx = {k: self._fund_flow_df.columns.get_loc(v)
                   for k, v in col_map.items() if v in self._fund_flow_df.columns}

        sell_items = []
        buy_items = []
        in_sell_section = False
        in_buy_section = False

        for row in self._fund_flow_df.itertuples(index=False):
            item = str(row[col_idx.get('item', 0)] or '').strip()
            amt = self._safe_float(row[col_idx.get('amount', 1)])
            desc = str(row[col_idx.get('desc', 2)] or '').strip()

            if '卖出' in item and '汇总' in item:
                in_sell_section, in_buy_section = True, False
                continue
            if '买入' in item and '汇总' in item:
                in_sell_section, in_buy_section = False, True
                continue
            if '小计' in item:
                continue

            if in_sell_section and amt > 0:
                sell_items.append({'item': item, 'amount': amt, 'desc': desc})
                fs.sell_total += amt
            elif in_buy_section and amt > 0:
                buy_items.append({'item': item, 'amount': amt, 'desc': desc})
                fs.buy_total += amt
            elif '净流动' in item:
                fs.net_flow = amt
            elif '追加' in item:
                fs.additional_capital = amt
            elif '费用' in item:
                fs.transaction_fee = amt

        fs.details_sell = sell_items
        fs.details_buy = buy_items
        self.fund_flow = fs
        return fs

    # ---- 对比分析 ----

    def get_comparison_metrics(self) -> Optional[PortfolioComparison]:
        """获取调仓前后的对比指标"""
        if self._comparison_df is None or self._comparison_df.empty:
            return None

        before = {}
        after = {}
        improvements = []

        col_map = self._resolve_cols(self._comparison_df, {
            'category': ['指标类别'], 'name': ['指标名称'],
            'before': ['调仓前数值'], 'after': ['调仓后数值'],
            'change': ['变化幅度'], 'direction': ['变化方向'],
            'note': ['说明']
        })
        col_idx = {k: self._comparison_df.columns.get_loc(v)
                   for k, v in col_map.items() if v in self._comparison_df.columns}

        for row in self._comparison_df.itertuples(index=False):
            metric_name = str(row[col_idx.get('name', 1)] or '').strip()
            b_val = row[col_idx.get('before', 2)] or ''
            a_val = row[col_idx.get('after', 3)] or ''
            direction = str(row[col_idx.get('direction', 4)] or '')
            note = str(row[col_idx.get('note', 5)] or '')

            try:
                b_num = float(b_val) if b_val not in ('', 'NaN', None) else b_val
                a_num = float(a_val) if a_val not in ('', 'NaN', None) else a_val
                before[metric_name] = b_num
                after[metric_name] = a_num
            except (ValueError, TypeError):
                before[metric_name] = str(b_val)
                after[metric_name] = str(a_val)

            if direction == '改善':
                changes_text = f"{b_val} → {a_val}"
                improvements.append(f"{metric_name}: {changes_text} ({note[:40]})")

        self.comparison = PortfolioComparison(
            metrics_before=before, metrics_after=after,
            improvements=improvements
        )
        return self.comparison

    # ---- 止损止盈规则导出 ----

    def export_sl_tp_rules(self) -> Dict[str, Dict]:
        """
        从complete_rebalancing_plan提取止损止盈规则，
        格式与 stop_loss_monitor.DEFAULT_RULES.assets 兼容。

        Returns:
            {code: {'name', 'base_price', 'stop_loss_price', 'take_profit_price',
                    'stop_loss_pct', 'take_profit_pct', ...}}
        """
        if self._full_plan_df is None or self._full_plan_df.empty:
            return {}

        col_map = self._resolve_cols(self._full_plan_df, {
            'code': ['证券代码'], 'name': ['证券名称'],
            'price': ['最新价(元)'],
            'sl_price': ['止损位(元)'], 'tp_price': ['止盈位(元)'],
            'current_weight': ['当前仓位(%)'],
            'target_weight': ['目标仓位(%)'],
            'industry': ['行业分类'],
            'action_type': ['操作类型'],
            'attention': ['需特别注意'],
        })

        col_idx = {k: self._full_plan_df.columns.get_loc(v)
                   for k, v in col_map.items() if v in self._full_plan_df.columns}

        rules = {}
        for row in self._full_plan_df.itertuples(index=False):
            raw_code = str(row[col_idx.get('code', 0)] or '').strip()
            code = self._normalize_code(raw_code)
            name = str(row[col_idx.get('name', 1)] or '')
            price = self._safe_float(row[col_idx.get('price', 2)])
            sl_price = self._safe_float(row[col_idx.get('sl_price', 3)])
            tp_price = self._safe_float(row[col_idx.get('tp_price', 4)])
            cur_w = self._safe_float(row[col_idx.get('current_weight', 5)])
            tgt_w = self._safe_float(row[col_idx.get('target_weight', 6)])

            if price <= 0:
                continue

            # 计算百分比
            sl_pct = round((sl_price - price) / price * 100, 1) if sl_price > 0 else 0
            tp_pct = round((tp_price - price) / price * 100, 1) if tp_price > 0 else 0

            # 操作类型映射到trailing_stop
            action_str = str(row[col_idx.get('action_type', 8)] or '维持')

            rules[code] = {
                'code': code,
                'name': name,
                'base_price': round(price, 2),
                'base_date': datetime.now().strftime('%Y-%m-%d'),
                'stop_loss_pct': sl_pct,
                'stop_loss_price': round(sl_price, 2),
                'take_profit_pct': tp_pct,
                'take_profit_price': round(tp_price, 2),
                'current_weight_pct': cur_w,
                'target_weight_pct': tgt_w,
                'position_weight': tgt_w / 100,
                'action_type': action_str,
                'trailing_stop': action_str in ('减持', '清仓'),
                'monitoring_indicators': [],
                'risk_level': self._infer_risk_level(sl_pct),
            }

        self.sl_tp_rules = rules
        return rules

    def sync_to_stop_loss_monitor(self, monitor=None):
        """
        将导出的SL/TP规则同步到 StopLossMonitor 实例。

        Args:
            monitor: 已有的StopLossMonitor实例，为None则创建新的

        Returns:
            更新后的 monitor 或 None (如果无数据)
        """
        if not self.sl_tp_rules:
            self.export_sl_tp_rules()
        if not self.sl_tp_rules:
            _log.warning("无可用的止损止盈规则用于同步")
            return None

        from stop_loss_monitor import StopLossMonitor, DEFAULT_RULES

        # 构建新规则字典，覆盖DEFAULT_RULES中的对应资产
        updated_assets = []
        for asset_def in DEFAULT_RULES.get('assets', []):
            code = asset_def['code']
            if code in self.sl_tp_rules:
                new_rule = self.sl_tp_rules[code]
                # 合并: 保留原规则中Excel没有的字段 (如monitoring_indicators, notes)
                merged = {**asset_def}
                merged.update({
                    'base_price': new_rule['base_price'],
                    'base_date': new_rule['base_date'],
                    'stop_loss_pct': new_rule['stop_loss_pct'],
                    'stop_loss_price': new_rule['stop_loss_price'],
                    'take_profit_pct': new_rule['take_profit_pct'],
                    'take_profit_price': new_rule['take_profit_price'],
                    'position_weight': new_rule['position_weight'],
                    'trailing_stop': new_rule['trailing_stop'],
                })
                updated_assets.append(merged)
            else:
                updated_assets.append(asset_def)

        # 补充Excel中有但原DEFAULT_RULES中没有的资产
        existing_codes = {a['code'] for a in updated_assets}
        for code, rule in self.sl_tp_rules.items():
            if code not in existing_codes:
                updated_assets.append({
                    'code': code,
                    'name': rule['name'],
                    'base_price': rule['base_price'],
                    'base_date': rule['base_date'],
                    'stop_loss_pct': rule['stop_loss_pct'],
                    'stop_loss_price': rule['stop_loss_price'],
                    'take_profit_pct': rule['take_profit_pct'],
                    'take_profit_price': rule['take_profit_price'],
                    'monitoring_indicators': [],
                    'position_weight': rule['position_weight'],
                    'risk_level': rule['risk_level'],
                    'trailing_stop': rule['trailing_stop'],
                    'notes': f"来自再平衡计划 ({rule['action_type']})",
                })

        custom_rules = {
            'version': '2.0-auto',
            'updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'notes': '由RebalancingEngine从Excel自动生成的规则 (覆盖基准价)',
            'assets': updated_assets,
            'global_settings': dict(DEFAULT_RULES.get('global_settings', {})),
        }

        # 保存为YAML供后续使用
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'config', 'stop_loss_rules_auto.yaml'
        )
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            yaml.dump(custom_rules, f, allow_unicode=True,
                      default_flow_style=False, sort_keys=False)

        _log.info("已同步 %d 条止损止盈规则至 %s", len(updated_assets), out_path)

        # 返回使用新规则的monitor
        if monitor is None:
            monitor = StopLossMonitor(rules_file=out_path)
        return monitor

    # ---- 报告生成 ----

    def generate_report(self, include_trades: bool = True,
                        include_fund_flow: bool = True,
                        include_comparison: bool = True) -> str:
        """生成综合再平衡报告"""
        lines = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        lines.append("=" * 80)
        lines.append(f"\U0001f4ca 再平衡执行报告")
        lines.append(f"生成时间: {now}")
        if self.loaded_at:
            lines.append(f"数据加载: {self.loaded_at}")
        lines.append("=" * 80)
        lines.append("")

        # 一、概览
        pending = self.get_pending_trades()
        executed_count = len(self.trade_orders) - len(pending)

        lines.append("\U0001f4af 总体概览")
        lines.append("-" * 60)
        lines.append(f"  监控标的数: {self.total_assets}")
        lines.append(f"  交易指令总数: {len(self.trade_orders)}")
        lines.append(f"  已执行: {executed_count}  待执行: {len(pending)}")

        if self.fund_flow.sell_total or self.fund_flow.buy_total:
            lines.append(f"  卖出回笼: \u00a5{self.fund_flow.sell_total:,.0f}")
            lines.append(f"  买入支出: \u00a5{self.fund_flow.buy_total:,.0f}")
            lines.append(f"  需追加资金: \u00a5{self.fund_flow.additional_capital:,.0f}")
        lines.append("")

        # 二、分批执行计划
        if include_trades and self.trade_orders:
            lines.append("\U0001f4cb 分批执行计划")
            lines.append("-" * 80)

            phase_labels = {
                BatchPhase.PHASE_1: "\U0001f534 第一批 (本周内 — 高优)",
                BatchPhase.PHASE_2: "\U0001f7e1 第二批 (1个月内)",
                BatchPhase.PHASE_3: "\U0001f7e2 第三批 (3个月内 — 防御)",
            }
            action_icons = {
                TradeAction.CLEAR: "\u274c", TradeAction.REDUCE: "\u2b07",
                TradeAction.INCREASE: "\u2b06", TradeAction.HOLD: "\U0001f6ab",
                TradeAction.NEW: "\u2795",
            }

            for phase in [BatchPhase.PHASE_1, BatchPhase.PHASE_2, BatchPhase.PHASE_3]:
                phase_orders = self.get_trades_by_phase(phase)
                if not phase_orders:
                    continue

                lines.append("")
                lines.append(phase_labels.get(phase, phase.value))
                lines.append(f"{'状态':<6} {'操作':<6} {'名称':<10} {'代码':<8} "
                             f"{'股数':>7} {'金额':>12} {'说明'}")
                lines.append("-" * 76)

                for o in phase_orders:
                    icon = action_icons.get(o.action, '?')
                    status = '\u2705' if o.executed else '\u25cb'
                    amt_str = f"\u00a5{o.estimated_amount:>10,.0f}" if o.estimated_amount else "-"

                    lines.append(
                        f"{status:<6} {icon}{o.action.value:<5} {o.name:<10} "
                        f"{o.code:<8} {o.target_shares:>+7,d} {amt_str:>12} "
                        f"{o.notes[:36]}"
                    )
            lines.append("")

        # 三、资金流向
        if include_fund_flow:
            ff = self.calculate_fund_flow()
            if ff.sell_total or ff.buy_total:
                lines.append("\U0001f4b0 资金流向明细")
                lines.append("-" * 60)

                lines.append("  卖出:")
                for d in ff.details_sell:
                    lines.append(f"    • {d['item']}: \u00a5{d['amount']:>10,.0f}  {d['desc']}")
                lines.append(f"    {'合计:':>22} \u00a5{ff.sell_total:>10,.0f}")

                lines.append("  买入:")
                for d in ff.details_buy:
                    lines.append(f"    • {d['item']}: \u00a5{d['amount']:>10,.0f}  {d['desc']}")
                lines.append(f"    {'合计:':>22} \u00a5{ff.buy_total:>10,.0f}")

                lines.append("")
                lines.append(f"  资金净流动: \u00a5{ff.net_flow:>+12,.0f}")
                lines.append(f"  交易费用:   \u00a5{ff.transaction_fee:>12,.2f}")
                lines.append(f"  需追加资金: \u00a5{ff.additional_capital:>12,.0f}")
                lines.append("")

        # 四、调仓效果对比
        if include_comparison and self.comparison:
            comp = self.comparison
            lines.append("\U0001f4ca 调仓效果对比")
            lines.append("-" * 60)

            if comp.improvements:
                lines.append("  关键改善:")
                for imp in comp.improvements[:10]:
                    lines.append(f"    ✓ {imp}")
            lines.append("")

            if comp.metrics_before and comp.metrics_after:
                lines.append(f"  {'指标':<20} {'调仓前':>14} {'调仓后':>14} {'变化':>10}")
                lines.append("  " + "-" * 56)
                for k in list(comp.metrics_before.keys())[:12]:
                    bv = comp.metrics_before.get(k, '-')
                    av = comp.metrics_after.get(k, '-')
                    try:
                        bf, af = float(bv), float(av)
                        chg = (af - bf) / abs(bf) * 100 if bf != 0 else 0
                        chg_s = f"{chg:+.1f}%"
                    except (ValueError, ZeroDivisionError, TypeError):
                        chg_s = "-"
                    lines.append(f"  {k:<20} {str(bv):>14} {str(av):>14} {chg_s:>10}")
            lines.append("")

        # 五、执行摘要要点
        if self._summary_df is not None and not self._summary_df.empty:
            lines.append("\U0001f4dd 执行要点与提醒")
            lines.append("-" * 60)
            col_cat = self._find_col(self._summary_df, ['类别'])
            col_item = self._find_col(self._summary_df, ['项目'])
            col_content = self._find_col(self._summary_df, ['内容'])
            col_pri = self._find_col(self._summary_df, ['优先级'])

            if all([col_cat, col_item, col_content]):
                cat_idx = list(self._summary_df.columns).index(col_cat)
                item_idx = list(self._summary_df.columns).index(col_item)
                content_idx = list(self._summary_df.columns).index(col_content)
                pri_idx = list(self._summary_df.columns).index(col_pri) if col_pri else -1
                for row in self._summary_df.itertuples(index=False):
                    cat = str(row[cat_idx] or '').strip()
                    item = str(row[item_idx] or '').strip()
                    content = str(row[content_idx] or '').strip()
                    pri = str(row[pri_idx] or '') if pri_idx >= 0 else ''
                    pri_icon = "\U0001f534" if pri == "高" else "\U0001f7e1" if pri == "中" else "\u26aa"
                    if cat and content:
                        lines.append(f"  {pri_icon} [{cat}] {item}: {content[:60]}")
            lines.append("")

        lines.append("=" * 80)
        lines.append(f"报告生成完成 | 数据来源: 6份Excel | 引擎版本: v2.0")
        lines.append("=" * 80)

        return '\n'.join(lines)

    # ================================================================
    # 内部方法
    # ================================================================

    _excel_cache: Dict[str, pd.DataFrame] = {}

    def _load_excel(self, filepath: str, label: str) -> Optional[pd.DataFrame]:
        """加载单个Excel文件 (带缓存)"""
        if filepath in self._excel_cache:
            return self._excel_cache[filepath]
        if not os.path.exists(filepath):
            err = f"[{label}] 文件不存在: {filepath}"
            self.load_errors.append(err)
            _log.warning(err)
            return None
        try:
            df = pd.read_excel(filepath)
            self._excel_cache[filepath] = df
            _log.info("[%s] 加载成功: %d 行 x %d 列", label, len(df), len(df.columns))
            return df
        except Exception as exc:
            err = f"[{label}] 读取失败: {exc}"
            self.load_errors.append(err)
            _log.error(err)
            return None

    def _post_load_process(self):
        """加载后的预处理"""
        self.build_trade_orders()
        self.calculate_fund_flow()
        self.get_comparison_metrics()
        self.export_sl_tp_rules()

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """在DataFrame列名中模糊匹配"""
        for c in candidates:
            for col in df.columns:
                if c.lower() in str(col).lower():
                    return col
        return candidates[0] if candidates else None

    @staticmethod
    def _resolve_cols(df: pd.DataFrame,
                      mapping: Dict[str, List[str]]) -> Dict[str, str]:
        """批量解析列名映射"""
        result = {}
        for key, candidates in mapping.items():
            result[key] = RebalancingEngine._find_col(df, candidates) or candidates[0]
        return result

    @staticmethod
    def _normalize_code(code: str) -> str:
        """标准化股票代码 (补零到6位)"""
        c = str(code).strip()
        if c.isdigit():
            return c.zfill(6)
        return c

    @staticmethod
    def _safe_int(val, default=0):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_float(val, default=0.0):
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_phase(s: str) -> BatchPhase:
        for p in BatchPhase:
            if p.value in s:
                return p
        return BatchPhase.PHASE_2

    @staticmethod
    def _parse_action(s: str) -> TradeAction:
        for a in TradeAction:
            if a.value in s:
                return a
        return TradeAction.HOLD

    @staticmethod
    def _calc_priority(action: TradeAction, phase: BatchPhase) -> str:
        if phase == BatchPhase.PHASE_1:
            return "高"
        if action in (TradeAction.CLEAR, TradeAction.REDUCE):
            return "高"
        if phase == BatchPhase.PHASE_3:
            return "低"
        return "中"

    @staticmethod
    def _infer_risk_level(stop_loss_pct: float) -> str:
        """根据止损幅度推断风险等级"""
        sl = abs(stop_loss_pct) if stop_loss_pct < 0 else 0
        if sl >= 20:
            return "high"
        if sl >= 12:
            return "medium"
        return "low"


# ============================================================
# CLI入口
# ============================================================

def print_report_cli(output_file: Optional[str] = None,
                     auto_sync_sl: bool = False):
    """CLI快捷入口: 加载数据 → 生成报告 → 可选输出文件"""
    import sys, io
    if sys.platform == 'win32' and not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("\U0001f9e0 初始化再平衡引擎...")
    engine = RebalancingEngine()
    ok = engine.load_all()

    if not ok:
        print(f"\u26a0\ufe0f 部分数据加载失败: {engine.load_errors}")

    if engine.is_loaded:
        print(f"\u2705 已加载 {engine.total_assets} 个标的数据")
        print(f"   交易指令: {len(engine.trade_orders)} 条")
        print(f"   待执行:   {len(engine.get_pending_trades())} 条")
        print()

        if auto_sync_sl:
            monitor = engine.sync_to_stop_loss_monitor()
            if monitor:
                quotes = {}  # 可在此传入实时行情
                alerts = monitor.check_all(quotes)
                from stop_loss_monitor import generate_risk_alert_report as gen_sl
                print(gen_sl(alerts, include_header=True))

        report = engine.generate_report()
        print(report)

        if output_file:
            out_dir = os.path.dirname(os.path.abspath(__file__))
            out_path = os.path.join(out_dir, 'reports', output_file)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n\U0001f4be 报告已保存: {out_path}")
    else:
        print("\u274c 无可用数据，请检查Excel文件路径")


if __name__ == '__main__':
    from utils.console_encoding import setup_utf8_console

    setup_utf8_console()

    import argparse
    parser = argparse.ArgumentParser(description='量化策略再平衡引擎')
    parser.add_argument('--output', '-o', default=None,
                        help='输出报告文件名 (保存在 reports/ 目录)')
    parser.add_argument('--sync-sl', action='store_true',
                        help='同时同步止损止盈规则并检查')
    args = parser.parse_args()

    print_report_cli(output_file=args.output, auto_sync_sl=args.sync_sl)
