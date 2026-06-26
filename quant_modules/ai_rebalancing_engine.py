# -*- coding: utf-8 -*-
"""
AI量化再平衡引擎 v4.0 — 双轨策略 + 风险平价 + 豆包Seed日内再平衡

基于2026交易计划优化版v2:
  - 双轨配置: 权益组合300万(7%) + 低风险理财4000万(93%)
  - 37只标的: 权益22只 + 低风险15只
  - 风险平价: 各类资产贡献相等风险
  - 黄金止损: -8%减半仓 / -12%清仓
  - 5日执行计划: Day1~Day5分批次建仓
  - 豆包Seed 2.0 Pro LLM: 盘中再平衡决策
  - 月度KPI: 净值/回撤/夏普/胜率追踪
"""

import os
import sys
import json
import yaml
import math
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("quant")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 可选依赖 ──────────────────────────────────────
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from quant_modules.decision_theories import run_full_theory_analysis
    DECISION_THEORIES_AVAILABLE = True
except ImportError:
    DECISION_THEORIES_AVAILABLE = False

try:
    from quant_modules.wind_mcp import get_realtime_price
    WIND_MCP_AVAILABLE = True
except ImportError:
    WIND_MCP_AVAILABLE = False

# ── 数据类 ──────────────────────────────────────

@dataclass
class TradeSignal:
    """交易信号"""
    code: str
    name: str
    action: str          # BUY / SELL / HOLD
    shares: int
    reason: str
    confidence: float = 0.5
    theory_signal: str = ""
    execution_batch: str = ""  # Day1~Day5
    stop_loss_triggered: bool = False
    category: str = ""


@dataclass
class RebalanceResult:
    """再平衡结果"""
    timestamp: str
    signals: List[TradeSignal]
    portfolio_weights: Dict[str, float]
    target_weights: Dict[str, float]
    cash_needed: float
    total_value: float
    theory_signals: Dict[str, Any] = field(default_factory=dict)
    llm_decision: str = ""
    execution_plan: Dict[str, List[str]] = field(default_factory=dict)
    monthly_kpi: Dict[str, Any] = field(default_factory=dict)
    risk_parity_weights: Dict[str, float] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# 配置文件加载
# ═══════════════════════════════════════════════════════════

def _load_portfolio_yaml() -> dict:
    """从 portfolio.yaml 加载配置"""
    yaml_path = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
    if os.path.exists(yaml_path):
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


def _build_portfolio_config() -> Dict[str, dict]:
    """从 YAML 构建 PORTFOLIO_CONFIG 字典"""
    yaml_cfg = _load_portfolio_yaml()
    assets = yaml_cfg.get('assets', [])

    config = {}
    for a in assets:
        code = a.get('code', '')
        if not code or code == 'CASH':
            continue
        config[code] = {
            'name': a.get('name', code),
            'weight': float(a.get('target_weight', 0)),
            'category': a.get('category', 'unknown'),
            'stop_loss': float(a.get('stop_loss', 0)),
            'risk_weight': float(a.get('risk_weight', 0.15)),
        }
    return config


def get_global_config() -> dict:
    """获取全局配置"""
    yaml_cfg = _load_portfolio_yaml()
    return yaml_cfg.get('global', {})


# ═══════════════════════════════════════════════════════════
# 风险平价引擎
# ═══════════════════════════════════════════════════════════

class RiskParityEngine:
    """
    风险平价引擎 — 让每种资产对组合整体风险贡献相等

    公式: 配置权重_i = (1/σ_i) / Σ(1/σ_j)
    其中 σ_i = risk_weight (波动率代理)
    """

    def __init__(self):
        self._config = _build_portfolio_config()

    def compute_risk_parity_weights(
        self,
        total_capital: float = 43_000_000,
        equity_capital: float = 3_000_000
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        计算风险平价权重

        Returns:
            (total_weights, equity_weights) — 总账户和权益子组合权重
        """
        # 分离权益类和低风险类
        equity_assets = {}
        low_risk_assets = {}
        for code, cfg in self._config.items():
            if cfg['category'] in ('core_etf', 'tech_growth', 'manufacturing',
                                    'defensive', 'commodity'):
                equity_assets[code] = cfg
            else:
                low_risk_assets[code] = cfg

        # 权益组合风险平价
        inv_vol_sum_e = sum(1.0 / max(a['risk_weight'], 0.001) for a in equity_assets.values())
        equity_rp = {}
        for code, cfg in equity_assets.items():
            raw = (1.0 / max(cfg['risk_weight'], 0.001)) / inv_vol_sum_e if inv_vol_sum_e > 0 else 0
            equity_rp[code] = raw

        # 低风险组合风险平价
        inv_vol_sum_l = sum(1.0 / max(a['risk_weight'], 0.001) for a in low_risk_assets.values())
        low_risk_rp = {}
        for code, cfg in low_risk_assets.items():
            raw = (1.0 / max(cfg['risk_weight'], 0.001)) / inv_vol_sum_l if inv_vol_sum_l > 0 else 0
            low_risk_rp[code] = raw

        # 合并为总账户权重
        eq_ratio = equity_capital / total_capital if total_capital > 0 else 0.07
        lr_ratio = 1.0 - eq_ratio

        total_weights = {}
        for code, w in equity_rp.items():
            total_weights[code] = w * eq_ratio
        for code, w in low_risk_rp.items():
            total_weights[code] = w * lr_ratio

        return total_weights, equity_rp

    def get_category_risk_budget(self) -> Dict[str, float]:
        """计算各类别风险预算"""
        categories = {}
        for code, cfg in self._config.items():
            cat = cfg['category']
            categories.setdefault(cat, []).append(cfg['risk_weight'])

        budget = {}
        for cat, risks in categories.items():
            budget[cat] = {
                'count': len(risks),
                'avg_risk': sum(risks) / len(risks) if risks else 0,
                'max_risk': max(risks) if risks else 0,
                'total_risk': sum(risks),
            }
        return budget


# ═══════════════════════════════════════════════════════════
# 黄金止损策略
# ═══════════════════════════════════════════════════════════

class GoldStopLossStrategy:
    """
    黄金ETF专用止损策略

    基于历史波动率18.88%、最大回撤-28.08%优化:
      -8%  → 减半仓 (覆盖~1.5σ，避免误触发)
      -12% → 清仓   (~2σ外，控制极端损失)

    历史回测: 2024-2026年仅触发1次减半仓、0次清仓
    """

    HALF_THRESHOLD = -0.08
    CLEAR_THRESHOLD = -0.12

    @classmethod
    def evaluate(cls, code: str, unrealized_pnl_pct: float,
                 current_shares: int) -> Optional[TradeSignal]:
        """评估黄金止损"""
        if code != '518880':
            return None

        if unrealized_pnl_pct <= cls.CLEAR_THRESHOLD:
            return TradeSignal(
                code=code, name='黄金ETF华安', action='SELL',
                shares=current_shares,
                reason=f'黄金止损清仓 ({unrealized_pnl_pct:.1%} ≤ -12%)',
                confidence=0.95, stop_loss_triggered=True,
                category='commodity'
            )
        elif unrealized_pnl_pct <= cls.HALF_THRESHOLD:
            half_shares = max(int(current_shares / 2 / 100) * 100, 100)
            return TradeSignal(
                code=code, name='黄金ETF华安', action='SELL',
                shares=half_shares,
                reason=f'黄金止损减半 ({unrealized_pnl_pct:.1%} ≤ -8%)',
                confidence=0.85, stop_loss_triggered=True,
                category='commodity'
            )
        return None


# ═══════════════════════════════════════════════════════════
# 信号聚合器
# ═══════════════════════════════════════════════════════════

class SignalAggregator:
    """信号聚合器 — 整合多理论信号 + 贝叶斯加权"""

    @staticmethod
    def aggregate(signals: List[Dict], prior_confidence: float = 0.5) -> Tuple[str, float]:
        """
        贝叶斯加权聚合多个理论信号

        每个理论的信号乘以该理论的置信度权重后求和，
        最终得到加权后的 (action, confidence)
        """
        if not signals:
            return "HOLD", prior_confidence

        weights = {'BUY': 0.0, 'SELL': 0.0, 'HOLD': 0.0}
        total_confidence = 0.0

        for s in signals:
            action = s.get('action', 'HOLD')
            conf = s.get('confidence', 0.5)
            weights[action] += conf
            total_confidence += conf

        if total_confidence == 0:
            return "HOLD", prior_confidence

        # 归一化
        buy_ratio = weights['BUY'] / total_confidence
        sell_ratio = weights['SELL'] / total_confidence

        if buy_ratio >= 0.55:
            return "BUY", buy_ratio
        elif sell_ratio >= 0.55:
            return "SELL", sell_ratio
        else:
            return "HOLD", max(buy_ratio, sell_ratio, 0.3)

    @staticmethod
    def theory_to_dict(theory_name: str, decision) -> Dict:
        """将 TheoryDecision 转为标准字典"""
        if hasattr(decision, 'to_dict'):
            d = decision.to_dict()
        elif isinstance(decision, dict):
            d = decision
        else:
            return {'theory': theory_name, 'action': 'HOLD', 'confidence': 0.0}

        return {
            'theory': theory_name,
            'action': d.get('signal', d.get('action', 'HOLD')),
            'confidence': d.get('score', d.get('confidence', 0.0)),
            'summary': d.get('summary', ''),
        }


# ═══════════════════════════════════════════════════════════
# 豆包 Seed LLM 盘中再平衡
# ═══════════════════════════════════════════════════════════

class SeedRebalancer:
    """豆包 Speed 32k 盘中再平衡决策引擎"""

    MODEL = "doubao-speed-32k"
    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/responses"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("VOLCENGINE_API_KEY", "")
        self.model = os.environ.get("SEED_MODEL", self.MODEL)

    @property
    def available(self) -> bool:
        return bool(self.api_key) and HAS_REQUESTS

    def generate_intraday_decision(
        self,
        portfolio_data: Dict[str, Dict],
        theory_signals: Dict[str, Any],
        risk_parity_weights: Dict[str, float] = None,
        market_context: Dict[str, Any] = None,
        gold_stop_signal: TradeSignal = None
    ) -> str:
        """生成盘中再平衡决策"""
        if not self.available:
            return ""

        prompt = self._build_intraday_prompt(
            portfolio_data, theory_signals, risk_parity_weights,
            market_context, gold_stop_signal
        )

        try:
            # 豆包 Seed 使用 responses API 格式
            payload = {
                "model": self.model,
                "input": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            resp = requests.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=35
            )
            if resp.status_code == 200:
                data = resp.json()
                # 解析 responses API 格式
                for output in data.get('output', []):
                    if output.get('type') == 'message':
                        for content_item in output.get('content', []):
                            if content_item.get('type') == 'output_text':
                                return content_item.get('text', '')
                return data.get('output', [{}])[0].get('content', '')
            logger.warning(f"豆包Seed API error: {resp.status_code}")
            return ""
        except Exception as e:
            logger.warning(f"豆包Seed调用失败: {e}")
            return ""

    def _build_intraday_prompt(self, portfolio, theories, rp_weights,
                                market, gold_signal) -> str:
        """构建盘中决策提示词"""
        lines = [
            "## 盘中再平衡决策请求",
            "",
            f"**时间**: {datetime.now():%Y-%m-%d %H:%M}",
            "",
            "### 当前持仓与偏离",
            "| 代码 | 名称 | 类别 | 当前权重 | 目标权重 | 偏离 | 浮亏% | 止损线 |",
            "|------|------|------|----------|----------|------|-------|--------|",
        ]
        for code, d in portfolio_data.items():
            dev = d.get('target_weight', 0) - d.get('current_weight', 0)
            lines.append(
                f"| {code} | {d.get('name','')} | {d.get('category','')} | "
                f"{d.get('current_weight',0):.2%} | {d.get('target_weight',0):.2%} | "
                f"{dev:+.2%} | {d.get('unrealized_pnl_pct',0):.1f}% | "
                f"{d.get('stop_loss',0):.0%} |"
            )

        if rp_weights:
            lines.append("\n### 风险平价建议权重")
            for code, w in sorted(rp_weights.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"- {code}: {w:.4%}")

        if gold_signal:
            lines.append(f"\n### 黄金止损信号")
            lines.append(f"- {gold_signal.reason} (置信度 {gold_signal.confidence:.0%})")

        if theories:
            lines.append("\n### 四大理论信号")
            for theory, sig in theories.items():
                if isinstance(sig, dict):
                    lines.append(
                        f"- {theory}: {sig.get('action','HOLD')} "
                        f"(置信度 {sig.get('confidence',0):.0%})"
                    )

        if market:
            lines.append("\n### 市场环境")
            for k, v in market.items():
                lines.append(f"- {k}: {v}")

        lines.append("\n### 请给出:")
        lines.append("1. 是否需要立即调仓 (是/否)")
        lines.append("2. 优先操作哪些标的 (按紧急程度排序)")
        lines.append("3. 风险提示 (最大风险点)")
        lines.append("4. 建议执行批次 (盘中/收盘前/明日)")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 5日执行计划
# ═══════════════════════════════════════════════════════════

class ExecutionPlanner:
    """5日建仓/再平衡执行计划"""

    BATCH_SCHEDULE = {
        'Day1': ['510300', '510500', '512100', '515180', '600036', '600900', '601088',
                 '000105', '000084'],
        'Day2': ['688041', '300308', '300274', '002371', '000236', '000267'],
        'Day3': ['688017', '600276', '600089', '600875', '340001', '001816', '040022'],
        'Day4': ['588000', '159915', '000425', '600406', '600989', '515080', '512890', '510030'],
        'Day5': ['518880', '000311', '163407'],
    }

    BUILD_RULES = {
        'max_daily_pct': 0.20,       # 单日买入 ≤ 总资金20%
        'first_day_pct': 0.50,       # 首日建仓50%
        'min_cash_reserve': 240_000,  # 现金不低于24万
        'circuit_breaker': -0.03,     # 沪深300单日跌>3%暂停
    }

    @classmethod
    def assign_batch(cls, code: str) -> str:
        """分配标的到执行批次"""
        for batch, codes in cls.BATCH_SCHEDULE.items():
            if code in codes:
                return batch
        return 'Day5'

    @classmethod
    def build_plan(cls, signals: List[TradeSignal],
                   total_capital: float = 3_000_000) -> Dict[str, Any]:
        """构建执行计划"""
        plan = {f'Day{d}': {'buys': [], 'sells': [], 'amount': 0.0} for d in range(1, 6)}

        # 辅助: 代码→信号
        by_code = {}
        for s in signals:
            batch = s.execution_batch or cls.assign_batch(s.code)
            by_code.setdefault(batch, []).append(s)

        for batch, sigs in by_code.items():
            day_plan = plan.get(batch, {'buys': [], 'sells': [], 'amount': 0.0})
            for s in sigs:
                if s.action == 'BUY':
                    day_plan['buys'].append(s.code)
                else:
                    day_plan['sells'].append(s.code)
            plan[batch] = day_plan

        return {
            'schedule': cls.BATCH_SCHEDULE,
            'plan': plan,
            'rules': cls.BUILD_RULES,
            'total_capital': total_capital,
        }


# ═══════════════════════════════════════════════════════════
# 月度KPI追踪
# ═══════════════════════════════════════════════════════════

class MonthlyKPITracker:
    """月度KPI追踪器"""

    MONTHLY_TARGETS = {
        6:  {'nav_range': (0.98, 1.02), 'max_dd': 0.02, 'cash': 240_000, 'phase': '建仓'},
        7:  {'nav_range': (0.98, 1.05), 'max_dd': 0.03, 'cash': 240_000, 'phase': '观察'},
        8:  {'nav_range': (1.00, 1.08), 'max_dd': 0.05, 'cash': 200_000, 'phase': 'Q2财报应对'},
        9:  {'nav_range': (1.03, 1.12), 'max_dd': 0.06, 'cash': 240_000, 'phase': '半年度评估'},
        10: {'nav_range': (1.05, 1.18), 'max_dd': 0.08, 'cash': 150_000, 'phase': 'Q4进攻'},
        11: {'nav_range': (1.06, 1.22), 'max_dd': 0.06, 'cash': 200_000, 'phase': '锁定利润'},
        12: {'nav_range': (1.08, 1.25), 'max_dd': 0.15, 'cash': 750_000, 'phase': '年度收官'},
    }

    @classmethod
    def get_current_targets(cls, month: int = None) -> dict:
        """获取当月KPI目标"""
        if month is None:
            month = datetime.now().month
        return cls.MONTHLY_TARGETS.get(month, cls.MONTHLY_TARGETS[12])

    @classmethod
    def evaluate(cls, nav: float, max_dd: float, cash: float,
                 sharpe: float = 0, win_rate: float = 0) -> Dict[str, Any]:
        """评估当前KPI达成情况"""
        targets = cls.get_current_targets()
        nav_ok = targets['nav_range'][0] <= nav <= targets['nav_range'][1]
        dd_ok = max_dd <= targets['max_dd']

        return {
            'month': datetime.now().month,
            'phase': targets['phase'],
            'current_nav': nav,
            'nav_target': f"{targets['nav_range'][0]:.2f}~{targets['nav_range'][1]:.2f}",
            'nav_ok': nav_ok,
            'current_dd': max_dd,
            'dd_target': targets['max_dd'],
            'dd_ok': dd_ok,
            'current_cash': cash,
            'cash_target': targets['cash'],
            'sharpe': sharpe,
            'win_rate': win_rate,
            'overall': 'GREEN' if (nav_ok and dd_ok) else ('YELLOW' if nav_ok or dd_ok else 'RED'),
        }


# ═══════════════════════════════════════════════════════════
# AI量化再平衡引擎 v4.0
# ═══════════════════════════════════════════════════════════

class AIQuantRebalancingEngine:
    """
    AI量化再平衡引擎 v4.0

    整合:
      - 双轨配置 (权益300万 + 低风险4000万)
      - 风险平价权重
      - 四大理论信号
      - DeepSeek LLM盘中决策
      - 黄金分级止损
      - 5日执行计划
      - 月度KPI追踪

    使用:
        engine = AIQuantRebalancingEngine(total_capital=43_000_000)
        result = engine.analyze_portfolio(positions, prices)
    """

    def __init__(
        self,
        total_capital: float = 43_000_000,
        equity_capital: float = 3_000_000,
        use_llm: bool = True,
        use_theories: bool = True,
    ):
        self.total_capital = total_capital
        self.equity_capital = equity_capital
        self.low_risk_capital = total_capital - equity_capital
        self.use_llm = use_llm
        self.use_theories = use_theories
        self.cash_reserve_pct = 0.08

        # 从 portfolio.yaml 加载配置
        self.portfolio_config = _build_portfolio_config()

        # 子引擎
        self.risk_parity = RiskParityEngine()
        self.llm = DeepSeekRebalancer() if use_llm else None

        # 止损规则表 (从配置提取)
        self.stop_loss_table = {}
        for code, cfg in self.portfolio_config.items():
            self.stop_loss_table[code] = abs(cfg.get('stop_loss', 0.10))

    # ── 主入口 ──────────────────────────────────

    def analyze_portfolio(
        self,
        positions: Dict[str, Dict],
        prices: Dict[str, float] = None,
        market_context: Dict[str, Any] = None
    ) -> RebalanceResult:
        """分析组合，生成再平衡信号"""

        # 1. 计算当前权重
        portfolio_data, total_value = self._calc_weights(positions, prices or {})

        # 2. 风险平价权重
        total_rp, equity_rp = self.risk_parity.compute_risk_parity_weights(
            self.total_capital, self.equity_capital
        )

        # 3. 四大理论信号
        theory_signals = {}
        if self.use_theories and DECISION_THEORIES_AVAILABLE and prices:
            theory_signals = self._get_theory_signals(prices, portfolio_data)

        # 4. 黄金止损检测
        gold_signal = None
        for code, data in portfolio_data.items():
            if code == '518880':
                gold_signal = GoldStopLossStrategy.evaluate(
                    code, data.get('unrealized_pnl_pct', 0),
                    data.get('shares', 0)
                )

        # 5. 生成交易信号
        signals = self._generate_signals(
            portfolio_data, theory_signals, prices or {}, gold_signal
        )

        # 6. DeepSeek LLM 决策
        llm_decision = ""
        if self.llm and self.llm.available:
            llm_decision = self.llm.generate_intraday_decision(
                portfolio_data, theory_signals, equity_rp,
                market_context, gold_signal
            )

        # 7. 执行计划
        execution_plan = ExecutionPlanner.build_plan(signals, self.equity_capital)

        # 8. 月度KPI
        total_nav = total_value / self.equity_capital if self.equity_capital > 0 else 1.0
        monthly_kpi = MonthlyKPITracker.evaluate(
            nav=total_nav,
            max_dd=0.0,  # 需要历史数据
            cash=self.total_capital * self.cash_reserve_pct,
        )

        # 9. 现金需求
        cash_needed = sum(
            s.shares * prices.get(s.code, 0) for s in signals if s.action == "BUY"
        ) - sum(
            s.shares * prices.get(s.code, 0) for s in signals if s.action == "SELL"
        )

        return RebalanceResult(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            signals=signals,
            portfolio_weights={k: v.get("current_weight", 0) for k, v in portfolio_data.items()},
            target_weights={k: self.portfolio_config.get(k, {}).get('weight', 0)
                           for k in portfolio_data},
            cash_needed=cash_needed,
            total_value=total_value,
            theory_signals=theory_signals,
            llm_decision=llm_decision,
            execution_plan=execution_plan,
            monthly_kpi=monthly_kpi,
            risk_parity_weights=equity_rp,
        )

    # ── 内部方法 ────────────────────────────────

    def _calc_weights(self, positions: Dict[str, Dict],
                      prices: Dict[str, float]) -> Tuple[Dict[str, Dict], float]:
        """计算当前权重"""
        total_value = 0.0
        market_values = {}

        for code, pos in positions.items():
            shares = pos.get("shares", 0)
            price = prices.get(code) or pos.get("avg_cost", 0) or 0
            mv = shares * price
            market_values[code] = mv
            total_value += mv

        result = {}
        for code, cfg in self.portfolio_config.items():
            mv = market_values.get(code, 0)
            shares = positions.get(code, {}).get("shares", 0)
            cost = positions.get(code, {}).get("cost", 0)
            avg_cost = positions.get(code, {}).get("avg_cost", mv / shares if shares > 0 else 0)

            unrealized_pnl = mv - cost if cost > 0 else 0
            unrealized_pnl_pct = (unrealized_pnl / cost) if cost > 0 else 0

            result[code] = {
                "name": cfg["name"],
                "shares": shares,
                "market_value": mv,
                "current_weight": mv / total_value if total_value > 0 else 0,
                "target_weight": cfg["weight"],
                "category": cfg["category"],
                "avg_cost": avg_cost,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
                "stop_loss": self.stop_loss_table.get(code, 0.10),
            }

        return result, total_value

    def _get_theory_signals(self, prices: Dict[str, float],
                            portfolio_data: Dict[str, Dict]) -> Dict[str, Any]:
        """获取四大理论信号"""
        try:
            price_series = {}
            for code, price in prices.items():
                price_series[code] = {
                    "price": price, "change_1d": 0,
                    "change_5d": 0, "change_20d": 0,
                }

            results = run_full_theory_analysis(
                price_data=price_series,
                macro_data={"pmi": 50, "cpi": 1.5},
                sector_map={code: d["category"] for code, d in portfolio_data.items()}
            )

            formatted = {}
            for theory_name, decision in (results or {}).items():
                formatted[theory_name] = SignalAggregator.theory_to_dict(theory_name, decision)

            return formatted
        except Exception as e:
            logger.warning(f"理论信号获取失败: {e}")
            return {}

    def _generate_signals(
        self,
        portfolio_data: Dict[str, Dict],
        theory_signals: Dict[str, Any],
        prices: Dict[str, float],
        gold_signal: TradeSignal = None
    ) -> List[TradeSignal]:
        """生成交易信号 — 权重偏离 + 止损 + 理论增强"""
        signals = []
        threshold = 0.03

        # 黄金止损信号优先
        if gold_signal:
            signals.append(gold_signal)

        for code, data in portfolio_data.items():
            # 跳过已由黄金止损处理的
            if code == '518880' and gold_signal:
                continue

            current_w = data["current_weight"]
            target_w = data["target_weight"]
            deviation = target_w - current_w
            price = prices.get(code) or data.get("avg_cost") or 0

            # 止损检查
            if data["unrealized_pnl_pct"] < -data["stop_loss"]:
                shares = self._calc_shares(abs(deviation) * self.equity_capital, price)
                if shares > 0:
                    signals.append(TradeSignal(
                        code=code, name=data["name"], action="SELL",
                        shares=shares,
                        reason=f"止损 ({data['unrealized_pnl_pct']:.1%} < -{data['stop_loss']:.0%})",
                        confidence=0.88, stop_loss_triggered=True,
                        category=data["category"]
                    ))
                continue

            # 权重偏离
            if abs(deviation) <= threshold:
                continue

            shares = self._calc_shares(abs(deviation) * self.equity_capital, price)
            if shares < 100:
                continue

            action = "BUY" if deviation > 0 else "SELL"
            reason = (
                f"低配 {deviation:+.2%} → 增持" if deviation > 0
                else f"超配 {deviation:+.2%} → 减持"
            )

            # 理论信号加权
            confidence = 0.60
            theory_action = ""
            for tname, tsig in theory_signals.items():
                ta = tsig.get('action', '')
                if ta == action:
                    confidence = max(confidence, 0.78)
                    theory_action = tname
                elif ta and ta != 'HOLD' and ta != action:
                    confidence *= 0.85  # 有冲突，降低置信度

            batch = ExecutionPlanner.assign_batch(code)

            signals.append(TradeSignal(
                code=code, name=data["name"], action=action,
                shares=shares, reason=reason, confidence=confidence,
                theory_signal=theory_action, execution_batch=batch,
                category=data["category"]
            ))

        return sorted(signals, key=lambda s: s.confidence, reverse=True)

    @staticmethod
    def _calc_shares(amount: float, price: float) -> int:
        """计算交易股数 (100股整数倍)"""
        if price <= 0:
            return 0
        shares = int(amount / price / 100) * 100
        return max(shares, 0)


# ═══════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════

def run_ai_rebalance(
    positions: Dict[str, Dict],
    prices: Dict[str, float],
    total_capital: float = 43_000_000,
    equity_capital: float = 3_000_000,
    use_llm: bool = True,
    market_context: Dict[str, Any] = None,
) -> RebalanceResult:
    """一键运行AI量化再平衡"""
    engine = AIQuantRebalancingEngine(
        total_capital=total_capital,
        equity_capital=equity_capital,
        use_llm=use_llm,
    )
    return engine.analyze_portfolio(positions, prices, market_context)


# ═══════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("AI量化再平衡引擎 v4.0 — 自检")
    print("=" * 70)

    # 配置加载
    cfg = _build_portfolio_config()
    print(f"\n配置加载: {len(cfg)} 只标的")
    cats = {}
    for c, d in cfg.items():
        cats[d['category']] = cats.get(d['category'], 0) + 1
    for cat, cnt in sorted(cats.items()):
        print(f"  {cat}: {cnt}只")

    # 风险平价
    rp = RiskParityEngine()
    tw, ew = rp.compute_risk_parity_weights()
    print(f"\n风险平价: {len(ew)} 权益标的, {len(tw)} 总标的")
    top5 = sorted(ew.items(), key=lambda x: -x[1])[:5]
    for code, w in top5:
        print(f"  {code} {cfg.get(code,{}).get('name','')}: {w:.4%}")

    # 黄金止损
    print(f"\n黄金止损策略:")
    print(f"  减半阈值: {GoldStopLossStrategy.HALF_THRESHOLD:.0%}")
    print(f"  清仓阈值: {GoldStopLossStrategy.CLEAR_THRESHOLD:.0%}")

    # 执行计划
    print(f"\n5日执行计划批次:")
    for batch, codes in ExecutionPlanner.BATCH_SCHEDULE.items():
        print(f"  {batch}: {len(codes)}只")

    # 月度KPI
    kpi = MonthlyKPITracker.evaluate(1.0, 0.0, 240_000, 0.65, 0.60)
    print(f"\n当前月度KPI (模拟):")
    print(f"  阶段: {kpi['phase']}")
    print(f"  NAV达标: {kpi['nav_ok']}, 回撤达标: {kpi['dd_ok']}")
    print(f"  综合: {kpi['overall']}")

    # DeepSeek状态
    llm = DeepSeekRebalancer()
    print(f"\nDeepSeek LLM: {'可用' if llm.available else '未配置API Key'}")

    # 理论引擎
    print(f"四大理论引擎: {'可用' if DECISION_THEORIES_AVAILABLE else '不可用'}")
    print(f"Wind MCP: {'可用' if WIND_MCP_AVAILABLE else '不可用'}")

    print("\n" + "=" * 70)
    print("自检完成")
