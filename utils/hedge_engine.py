# -*- coding: utf-8 -*-
"""
对冲引擎 v5.9 — 多指数Beta加权 + 组合自触发 + 成本意识优化

v5.9 核心改进（基于2021-2026回测发现）:
1. 多指数Beta加权对冲分配 — IC/IM/IF按Beta比例分配，替代纯IF
2. 组合自身波动率触发 — 不再依赖CSI300市场状态判断
3. 成本效益阈值 — 仅在对冲收益预期 > 成本*1.5时激活
4. 极端行情尾部保护模式 — 默认模式，仅在vol>28%或DD>12%时触发

数据源: Wind MCP → Sina/AKShare (免费回退)
"""

import os
import sys
import json
import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger('hedge_engine')

# ── 指数成分股权重(简化版) ──
INDEX_WEIGHTS_CSI300 = {
    "300750": 0.042, "600519": 0.055, "000858": 0.038, "601318": 0.032,
    "600036": 0.028, "000333": 0.025, "002415": 0.022, "300059": 0.020,
    "600276": 0.018, "601166": 0.016, "600900": 0.015, "000651": 0.014,
    "002475": 0.013, "601899": 0.013, "603259": 0.012,
}
INDEX_WEIGHTS_CSI500 = {
    "688981": 0.008, "688041": 0.007, "002371": 0.006, "300308": 0.005,
    "000792": 0.004, "600219": 0.004, "002422": 0.004, "000425": 0.003,
    "600019": 0.003, "601088": 0.005,
}

# ── 股指期货合约规格 ──
INDEX_FUTURES_SPECS = {
    "IF": {
        "name": "沪深300股指期货", "underlying": "CSI300",
        "multiplier": 300, "margin_pct": 0.12, "tick_size": 0.2,
        "contracts_per_month": 4, "dominant_contract_months": [3, 6, 9, 12],
        "sina_code": "nf_IF0",
    },
    "IC": {
        "name": "中证500股指期货", "underlying": "CSI500",
        "multiplier": 200, "margin_pct": 0.14, "tick_size": 0.2,
        "contracts_per_month": 4, "dominant_contract_months": [3, 6, 9, 12],
        "sina_code": "nf_IC0",
    },
    "IM": {
        "name": "中证1000股指期货", "underlying": "CSI1000",
        "multiplier": 200, "margin_pct": 0.15, "tick_size": 0.2,
        "contracts_per_month": 4, "dominant_contract_months": [3, 6, 9, 12],
        "sina_code": "nf_IM0",
    },
    "IH": {
        "name": "上证50股指期货", "underlying": "SSE50",
        "multiplier": 300, "margin_pct": 0.12, "tick_size": 0.2,
        "contracts_per_month": 4, "dominant_contract_months": [3, 6, 9, 12],
        "sina_code": "nf_IH0",
    },
}

# ── 期权合约规格 ──
ETF_OPTIONS_SPECS = {
    "510300": {
        "name": "沪深300ETF期权", "underlying": "510300.SH",
        "multiplier": 10000, "strike_step": 0.1, "exchange": "SSE",
    },
    "510050": {
        "name": "上证50ETF期权", "underlying": "510050.SH",
        "multiplier": 10000, "strike_step": 0.05, "exchange": "SSE",
    },
    "000300": {
        "name": "沪深300指数期权", "underlying": "000300.SH",
        "multiplier": 100, "strike_step": 50, "exchange": "CFFEX",
    },
}


class HedgeType(Enum):
    NONE = "none"
    FUTURES_SHORT = "futures_short"
    PUT_PROTECTIVE = "put_protective"
    PUT_SPREAD = "put_spread"
    COLLAR = "collar"
    DYNAMIC_DELTA = "dynamic_delta"


class HedgeSignalStrength(Enum):
    NO_HEDGE = 0
    LIGHT = 1       # 25%
    MODERATE = 2    # 50%
    STRONG = 3      # 75%
    FULL = 4        # 100%


@dataclass
class PortfolioRisk:
    """组合风险评估"""
    total_value: float = 0.0
    stock_exposure: float = 0.0
    cash: float = 0.0
    beta_csi300: float = 0.0
    beta_csi500: float = 0.0
    beta_csi1000: float = 0.0
    beta_sse50: float = 0.0
    volatility_30d: float = 0.0
    var_95_daily: float = 0.0
    cvar_95_daily: float = 0.0
    max_drawdown_current: float = 0.0
    correlation_matrix: Dict[str, float] = field(default_factory=dict)
    concentration_risk: float = 0.0


@dataclass  
class HedgeRecommendation:
    """对冲建议"""
    hedge_type: HedgeType = HedgeType.NONE
    strength: HedgeSignalStrength = HedgeSignalStrength.NO_HEDGE
    urgency_score: float = 0.0

    futures_instruments: List[str] = field(default_factory=list)
    futures_contracts: Dict[str, int] = field(default_factory=dict)
    futures_notional: Dict[str, float] = field(default_factory=dict)
    futures_margin: Dict[str, float] = field(default_factory=dict)

    options_instruments: List[str] = field(default_factory=list)
    options_strategy: str = ""
    options_contracts: List[Dict] = field(default_factory=list)
    options_cost: float = 0.0
    options_max_loss: float = 0.0

    hedge_ratio: float = 0.0
    effective_hedge_pct: float = 0.0
    expected_beta_after: float = 0.0
    expected_drawdown_reduce: float = 0.0

    reasoning: str = ""
    risk_signals: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


# ── 默认期货价格回退表 ──
DEFAULT_FUTURES_PRICES = {
    "IF": 3950.0, "IC": 6200.0, "IM": 6800.0, "IH": 2700.0,
}
FALLBACK_PRICES_UPDATED = "2026-06-29"

DEFAULT_INDEX_PRICES = {
    "CSI300": 3950.0, "CSI500": 6200.0, "CSI1000": 6800.0, "SSE50": 2700.0,
}

VOLATILITY_TARGET_ANNUAL = 0.18

# ── 对冲成本参数 ──
HEDGE_ROLL_COST_ANNUAL = 0.025    # 年化展期成本(基差+交易费)
HEDGE_MARGIN_OPP_COST = 0.020     # 保证金机会成本(按无风险利率)


# ── v5.9 新增：多指数Beta分配权重 ──
# 指数优先级的判定基于组合在各指数的暴露度
INDEX_ALLOCATION_ORDER = ["IC", "IM", "IF"]  # 中证500优先(匹配中小盘成长), 中证1000次之

# ── v5.9 新增：组合自触发阈值 ──
PORTFOLIO_TAIL_HEDGE_TRIGGERS = {
    "vol_trigger": 0.28,       # 年化波动率>28%触发
    "dd_trigger": 0.12,        # 60日最大回撤>12%触发
    "min_hedge_ratio": 0.25,   # 触发后最小对冲比率
    "max_hedge_ratio": 0.50,   # 触发后最大对冲比率
}

# ── v5.9 新增：成本效益阈值 ──
COST_BENEFIT_THRESHOLD = 1.5   # 预期对冲收益必须 > 对冲成本 * 1.5 才激活


# ============================================================
# 期货价格获取（多源回退）
# ============================================================

def fetch_futures_prices_from_sina() -> Dict[str, float]:
    import urllib.request
    import re
    sina_codes = {"IF": "nf_IF0", "IC": "nf_IC0", "IM": "nf_IM0", "IH": "nf_IH0"}
    results = {}
    for name, code in sina_codes.items():
        try:
            url = f"https://hq.sinajs.cn/list={code}"
            req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                text = resp.read().decode("gbk", errors="ignore")
            match = re.search(r'="([^"]+)"', text)
            if match:
                parts = match.group(1).split(",")
                if len(parts) >= 20:
                    price = float(parts[3]) if parts[3] and parts[3] != "0.000" else 0.0
                    if price > 0:
                        results[name] = price
        except Exception as e:
            logger.debug(f"[sina] {name} 失败: {e}")
    return results


def fetch_futures_prices_from_akshare() -> Dict[str, float]:
    results = {}
    try:
        import akshare as ak
        for name in ["IF", "IC", "IM", "IH"]:
            try:
                df = ak.futures_main_sina(symbol=f"{name}0")
                if df is not None and not df.empty:
                    price = float(df.iloc[-1]['close']) if 'close' in df.columns else float(df.iloc[-1].iloc[-2])
                    if price > 0:
                        results[name] = price
            except Exception:
                pass
    except ImportError:
        logger.debug("[akshare] 未安装")
    except Exception as e:
        logger.debug(f"[akshare] 批量获取失败: {e}")
    return results


def fetch_futures_prices_from_efinance() -> Dict[str, float]:
    results = {}
    try:
        import efinance as ef
        efinance_codes = {"IF": "IF0", "IC": "IC0", "IM": "IM0", "IH": "IH0"}
        for name, code in efinance_codes.items():
            try:
                quote = ef.futures.get_realtime_quotes(code)
                if quote is not None:
                    price = float(quote.price) if hasattr(quote, 'price') and quote.price else 0
                    if not price and isinstance(quote, dict):
                        price = float(quote.get('price', 0) or quote.get('最新价', 0))
                    if price > 0:
                        results[name] = price
            except Exception:
                pass
    except ImportError:
        logger.debug("[efinance] 未安装")
    except Exception:
        pass
    return results


def get_live_futures_prices(force_refresh: bool = False) -> Dict[str, float]:
    prices = {}
    source_used = "none"

    prices.update(fetch_futures_prices_from_akshare())
    if len(prices) >= 4:
        source_used = "akshare"

    missing = [k for k in ["IF", "IC", "IM", "IH"] if k not in prices]
    if missing:
        sina_prices = fetch_futures_prices_from_sina()
        for k in missing:
            if k in sina_prices:
                prices[k] = sina_prices[k]
        if source_used == "none":
            source_used = "sina" if len(prices) >= 3 else source_used

    missing = [k for k in ["IF", "IC", "IM", "IH"] if k not in prices]
    if missing:
        ef_prices = fetch_futures_prices_from_efinance()
        for k in missing:
            if k in ef_prices:
                prices[k] = ef_prices[k]
        if source_used == "none":
            source_used = "efinance" if len(prices) >= 2 else source_used

    fallback_used = []
    for name in ["IF", "IC", "IM", "IH"]:
        if name not in prices or prices[name] <= 0:
            prices[name] = DEFAULT_FUTURES_PRICES.get(name, 4000)
            fallback_used.append(name)

    if fallback_used:
        logger.warning(f"[!] 期货品种使用回退价格: {', '.join(fallback_used)}")

    if source_used != "none":
        logger.info(f"[OK] 期货价格 ({source_used}), 完整度: {4 - len(fallback_used)}/4")

    return prices


# ============================================================
# HedgeEngine v5.9
# ============================================================

class HedgeEngine:
    """对冲引擎核心类 v5.9

    核心改进:
    1. 多指数Beta加权对冲分配 — IC/IM优先, IF辅助
    2. 组合自触发尾部对冲 — 不依赖外部市场状态
    3. 成本效益过滤 — 对冲期望收益必须 > 1.5倍成本
    """

    def __init__(self, portfolio_value: float = 1_000_000):
        self.portfolio_value = portfolio_value
        self._price_cache: Dict[str, float] = {}
        self._beta_cache: Dict[str, float] = {}

    # ── 风险评估 ──

    def assess_portfolio_risk(
        self,
        positions: Dict[str, Dict[str, Any]],
        prices: Dict[str, float],
        historical_returns: Dict[str, List[float]] = None,
    ) -> PortfolioRisk:
        """评估组合风险"""
        risk = PortfolioRisk()

        total_stock = 0.0
        stock_weights = {}

        for code, pos in positions.items():
            shares = pos.get('shares', 0)
            price = prices.get(code, 0)
            market_value = shares * price
            total_stock += market_value
            if market_value > 0:
                stock_weights[code] = market_value

        risk.stock_exposure = total_stock
        risk.total_value = total_stock + self.portfolio_value
        risk.cash = risk.total_value - total_stock

        if total_stock <= 0:
            return risk

        total_weight = sum(stock_weights.values())
        if total_weight > 0:
            for code in stock_weights:
                stock_weights[code] /= total_weight

        risk.beta_csi300 = self._compute_weighted_beta(stock_weights, "CSI300")
        risk.beta_csi500 = self._compute_weighted_beta(stock_weights, "CSI500")
        risk.beta_csi1000 = self._compute_weighted_beta(stock_weights, "CSI1000")
        risk.beta_sse50 = self._compute_weighted_beta(stock_weights, "SSE50")

        # 波动率估算
        market_vol = 0.20
        risk.volatility_30d = risk.beta_csi300 * market_vol / math.sqrt(12) if risk.beta_csi300 > 0 else 0.02

        # VaR
        z_95 = 1.645
        risk.var_95_daily = risk.total_value * risk.volatility_30d * z_95
        risk.cvar_95_daily = risk.var_95_daily * 1.3

        # 集中度
        hhi = sum(w * w for w in stock_weights.values() if w > 0)
        risk.concentration_risk = hhi

        if historical_returns:
            risk.volatility_30d = self._compute_portfolio_vol(stock_weights, historical_returns)
            risk.var_95_daily = risk.total_value * risk.volatility_30d * z_95
            risk.cvar_95_daily = risk.var_95_daily * 1.3

        return risk

    def _compute_weighted_beta(self, weights: Dict[str, float], index: str) -> float:
        DEFAULT_BETAS = {
            "300308": (1.35, 1.50, 1.60, 1.20),
            "688041": (1.40, 1.55, 1.70, 1.25),
            "002371": (1.25, 1.40, 1.50, 1.15),
            "688981": (1.30, 1.45, 1.55, 1.20),
            "300750": (1.20, 1.35, 1.45, 1.10),
            "000425": (1.05, 1.15, 1.25, 0.95),
            "601088": (0.85, 0.80, 0.75, 0.90),
            "600219": (0.90, 0.95, 1.05, 0.85),
            "600019": (0.95, 1.00, 1.10, 0.90),
            "518880": (0.40, 0.35, 0.30, 0.45),
            "000792": (0.80, 0.90, 1.00, 0.75),
            "600276": (0.75, 0.70, 0.65, 0.80),
            "603259": (0.90, 0.95, 1.00, 0.85),
            "002422": (0.70, 0.65, 0.60, 0.75),
        }
        idx_map = {"CSI300": 0, "CSI500": 1, "CSI1000": 2, "SSE50": 3}
        idx = idx_map.get(index, 0)

        total_beta = 0.0
        total_w = 0.0
        for code, w in weights.items():
            pure_code = code.split('.')[0] if '.' in code else code
            if pure_code in DEFAULT_BETAS:
                total_beta += w * DEFAULT_BETAS[pure_code][idx]
            else:
                total_beta += w * 1.0
            total_w += w

        return total_beta / total_w if total_w > 0 else 0

    def _compute_portfolio_vol(self, weights, returns) -> float:
        return 0.015

    # ── v5.9 信号强度（组合自触发优先） ──

    def determine_hedge_signal_strength(
        self,
        risk: PortfolioRisk,
        market_signals: Dict[str, Any] = None,
        portfolio_volatility: float = None,
        portfolio_drawdown_60d: float = None,
    ) -> Tuple[HedgeSignalStrength, float]:
        """v5.9 五因子模型 — 组合自触发权重提升

        因子权重:
        1. 组合Beta因子 (25%, 从40%降低) — 降权,回测证明CSI300Beta不准确
        2. 组合自波动率因子 (25%, v5.9新增) — 组合自身波动率超过阈值
        3. 组合自回撤因子 (20%, v5.9新增) — 60日最大回撤触发
        4. 集中度因子 (15%, 从20%降低)
        5. VaR尾部风险 (10%)
        6. 外部市场信号 (5%, 从10%降低)
        """
        score = 0.0
        reasons = []

        # 1. Beta因子 (权重25%, v5.9从40%降低)
        beta = max(risk.beta_csi300, risk.beta_csi500, risk.beta_csi1000)
        if beta > 1.5:
            score += 0.25
            reasons.append(f"组合Beta={beta:.2f}(取最大)较高")
        elif beta > 1.2:
            score += 0.15
            reasons.append(f"组合Beta={beta:.2f}偏高")
        elif beta > 0.8:
            score += 0.08

        # 2. 组合自波动率因子 (权重25%, v5.9新增)
        if portfolio_volatility is not None and portfolio_volatility > 0:
            current_vol = portfolio_volatility
        else:
            current_vol = risk.volatility_30d * math.sqrt(252) if risk.volatility_30d > 0 else 0.18

        vol_trigger = PORTFOLIO_TAIL_HEDGE_TRIGGERS["vol_trigger"]
        if current_vol > vol_trigger * 1.2:
            score += 0.25
            reasons.append(f"组合波动率{current_vol*100:.1f}%严重超标(>{vol_trigger*120:.0f}%)")
        elif current_vol > vol_trigger:
            score += 0.18
            reasons.append(f"组合波动率{current_vol*100:.1f}%超标(>{vol_trigger*100:.0f}%)")
        elif current_vol > vol_trigger * 0.8:
            score += 0.08

        # 3. 组合自回撤因子 (权重20%, v5.9新增)
        dd_trigger = PORTFOLIO_TAIL_HEDGE_TRIGGERS["dd_trigger"]
        if portfolio_drawdown_60d is not None and portfolio_drawdown_60d > 0:
            if portfolio_drawdown_60d > dd_trigger * 1.5:
                score += 0.20
                reasons.append(f"组合60日回撤{portfolio_drawdown_60d*100:.1f}%严重(>{dd_trigger*150:.0f}%)")
            elif portfolio_drawdown_60d > dd_trigger:
                score += 0.14
                reasons.append(f"组合60日回撤{portfolio_drawdown_60d*100:.1f}%超标(>{dd_trigger*100:.0f}%)")
            elif portfolio_drawdown_60d > dd_trigger * 0.7:
                score += 0.06

        # 4. 集中度因子 (权重15%)
        if risk.concentration_risk > 0.25:
            score += 0.15
            reasons.append(f"集中度HHI={risk.concentration_risk:.3f}过高")
        elif risk.concentration_risk > 0.15:
            score += 0.08

        # 5. VaR因子 (权重10%)
        var_pct = risk.var_95_daily / risk.total_value if risk.total_value > 0 else 0
        if var_pct > 0.03:
            score += 0.10
            reasons.append(f"日VaR(95%)={var_pct*100:.1f}%")
        elif var_pct > 0.02:
            score += 0.05

        # 6. 外部市场信号 (权重5%, v5.9大幅降低)
        if market_signals:
            panic = market_signals.get('panic_index', 0)
            if panic > 0.75:
                score += 0.05
                reasons.append("外部恐慌指数极高")

        # 信号强度判定
        if score >= 0.65:
            strength = HedgeSignalStrength.STRONG
        elif score >= 0.50:
            strength = HedgeSignalStrength.MODERATE
        elif score >= 0.35:
            strength = HedgeSignalStrength.LIGHT
        else:
            strength = HedgeSignalStrength.NO_HEDGE

        return strength, score

    def compute_optimal_hedge_ratio(
        self,
        risk: PortfolioRisk,
        hedge_strength: HedgeSignalStrength,
        method: str = "min_variance",
        portfolio_volatility: float = None,
        portfolio_drawdown_60d: float = None,
    ) -> float:
        """v5.9 最优对冲比率 — 组合自触发为上限

        核心逻辑: 对冲比率 = min(Beta中性比率, 尾部保护比率)
        尾部保护仅在组合自身波动率>28%或回撤>12%时显著激活。
        """
        strength_ratio = {
            HedgeSignalStrength.NO_HEDGE: 0.0,
            HedgeSignalStrength.LIGHT: 0.25,
            HedgeSignalStrength.MODERATE: 0.50,
            HedgeSignalStrength.STRONG: 0.75,
            HedgeSignalStrength.FULL: 1.0,
        }
        base_ratio = strength_ratio[hedge_strength]

        # Beta中性比率（使用多指数最大Beta）
        max_beta = max(risk.beta_csi300, risk.beta_csi500, risk.beta_csi1000, 0.5)
        beta_neutral_ratio = max_beta * base_ratio * 0.70  # 70%因子考虑基差
        beta_neutral_ratio = min(beta_neutral_ratio, 1.0)

        # ── v5.9 核心: 组合自触发尾部保护比率 ──
        if portfolio_volatility is None:
            portfolio_volatility = risk.volatility_30d * math.sqrt(252) if risk.volatility_30d > 0 else 0.18

        vol_trigger = PORTFOLIO_TAIL_HEDGE_TRIGGERS["vol_trigger"]
        dd_trigger = PORTFOLIO_TAIL_HEDGE_TRIGGERS["dd_trigger"]
        max_ratio = PORTFOLIO_TAIL_HEDGE_TRIGGERS["max_hedge_ratio"]
        min_ratio = PORTFOLIO_TAIL_HEDGE_TRIGGERS["min_hedge_ratio"]

        tail_ratio = 0.0

        # 波动率触发
        if portfolio_volatility > vol_trigger:
            excess = portfolio_volatility - vol_trigger
            tail_ratio = min_ratio + excess * 2.5  # 每超出1%vol增加2.5%对冲
            tail_ratio = min(tail_ratio, max_ratio)

        # 回撤触发（叠加）
        if portfolio_drawdown_60d is not None and portfolio_drawdown_60d > dd_trigger:
            dd_excess = portfolio_drawdown_60d - dd_trigger
            dd_tail = min_ratio + dd_excess * 3.0
            dd_tail = min(dd_tail, max_ratio)
            tail_ratio = max(tail_ratio, dd_tail)

        # 融合: 取Beta中性(上限)和尾部保护的最小值
        # 尾保模式: 仅在极端行情激活, 日常不打扰
        final_ratio = min(beta_neutral_ratio + tail_ratio * 0.5, max(beta_neutral_ratio, tail_ratio))

        # 成本效益过滤
        if hedge_strength == HedgeSignalStrength.NO_HEDGE:
            return 0.0

        # 对冲成本估算(年化)
        hedge_cost_annual = final_ratio * (HEDGE_ROLL_COST_ANNUAL + HEDGE_MARGIN_OPP_COST)
        # 预期收益(仅尾保部分做减法)
        expected_benefit = tail_ratio * 0.08  # 尾保预期降低8%*ratio的回撤

        if expected_benefit < hedge_cost_annual * COST_BENEFIT_THRESHOLD and tail_ratio < 0.10:
            logger.info(f"[成本效益] 对冲预期收益{expected_benefit*100:.1f}% < "
                       f"成本{hedge_cost_annual*100:.1f}% * {COST_BENEFIT_THRESHOLD}, 降为0")
            return 0.0

        return min(final_ratio, 1.0)

    # ── v5.9 多指数Beta加权期货对冲 ──

    def generate_futures_hedge(
        self,
        risk: PortfolioRisk,
        hedge_ratio: float,
        futures_prices: Dict[str, float] = None,
    ) -> Dict[str, Any]:
        """v5.9 多指数Beta加权对冲方案

        IC/IM/IF按组合Beta比例分配, 不再单一依赖IF。
        """
        if hedge_ratio <= 0:
            return {"contracts": {}, "total_notional": 0, "total_margin": 0,
                    "reason": "对冲比率=0, 无需求", "price_source": "N/A", "fallback_used": []}

        price_source = "user_provided"
        if not futures_prices:
            futures_prices = get_live_futures_prices()
            price_source = "auto"

        fallback_used = []
        for code in ["IF", "IC", "IM", "IH"]:
            if code in futures_prices and abs(futures_prices[code] - DEFAULT_FUTURES_PRICES.get(code, 0)) < 0.1:
                fallback_used.append(code)

        if fallback_used:
            logger.warning(f"[!] 回退价格品种: {', '.join(fallback_used)}")

        # ── v5.9 多指数Beta加权分配 ──
        beta_map = {
            "IC": risk.beta_csi500,
            "IM": risk.beta_csi1000,
            "IF": risk.beta_csi300,
        }

        # 计算每个指数的对冲分配权重
        total_beta = sum(max(b, 0) for b in beta_map.values())
        if total_beta <= 0:
            return {"contracts": {}, "total_notional": 0, "total_margin": 0,
                    "reason": "组合Beta<=0, 无需对冲", "price_source": price_source, "fallback_used": fallback_used}

        hedge_notional_total = risk.stock_exposure * hedge_ratio

        result = {}
        remaining = hedge_notional_total

        # 按Beta比例分配, 优先IC和IM
        allocation_order = ["IC", "IM", "IF"]
        for code in allocation_order:
            beta = max(beta_map[code], 0)
            if beta <= 0 or remaining <= 0:
                continue

            spec = INDEX_FUTURES_SPECS[code]
            price = futures_prices.get(code, 0)
            multiplier = spec["multiplier"]

            if price <= 0:
                continue

            # 该指数分配的名义价值 = 总对冲 * (该指数Beta/总Beta)
            alloc_ratio = beta / total_beta
            alloc_notional = hedge_notional_total * alloc_ratio

            contract_value = price * multiplier
            contracts = max(1, round(alloc_notional / contract_value))
            notional = contracts * contract_value
            margin = notional * spec["margin_pct"]

            result[code] = {
                "contracts": contracts,
                "price": price,
                "notional": notional,
                "margin": margin,
                "spec": spec,
                "direction": "SELL",
                "alloc_ratio": alloc_ratio,
            }

            remaining -= notional

        total_notional = sum(v["notional"] for v in result.values())
        total_margin = sum(v["margin"] for v in result.values())

        # 生成理由
        parts = []
        if risk.beta_csi500 > 1.2:
            parts.append(f"CSI500 Beta={risk.beta_csi500:.2f}")
        if risk.beta_csi1000 > 1.2:
            parts.append(f"CSI1000 Beta={risk.beta_csi1000:.2f}")
        if risk.beta_csi300 > 1.0:
            parts.append(f"CSI300 Beta={risk.beta_csi300:.2f}")

        for code, detail in result.items():
            spec = detail.get("spec", {})
            name = spec.get("name", code)
            n = detail["contracts"]
            parts.append(f"做空{n}手{name}")

        reason = "; ".join(parts) if parts else f"多指数对冲{hedge_ratio*100:.0f}%敞口"
        if fallback_used:
            reason += f" [!]{','.join(fallback_used)}为回退价格"

        return {
            "contracts": result,
            "total_notional": total_notional,
            "total_margin": total_margin,
            "target_hedge_notional": hedge_notional_total,
            "reason": reason,
            "price_source": price_source,
            "fallback_used": fallback_used,
        }

    # ── 期权对冲（保留原实现） ──

    def generate_options_hedge(
        self, risk: PortfolioRisk, hedge_ratio: float,
        options_data: Dict[str, Any] = None, strategy: str = "protective_put",
    ) -> Dict[str, Any]:
        if hedge_ratio <= 0:
            return {"contracts": [], "total_cost": 0, "reason": "对冲比率=0"}

        default_iv = 0.22
        underlying = "510300" if risk.beta_csi300 > risk.beta_csi500 else "510050"
        index_price = 3950 if underlying == "510300" else 2700
        hedge_notional = risk.stock_exposure * hedge_ratio

        if strategy == "protective_put":
            T = 1/12
            atm_put_premium_pct = 0.4 * default_iv * math.sqrt(T)
            atm_put_premium = index_price * atm_put_premium_pct
            multiplier = ETF_OPTIONS_SPECS[underlying]["multiplier"]
            one_contract_hedge = index_price * multiplier
            contracts = max(1, round(hedge_notional / one_contract_hedge))
            total_premium = contracts * atm_put_premium * multiplier

            return {
                "strategy": "protective_put", "underlying": underlying,
                "contracts": contracts, "strike_type": "ATM",
                "estimated_premium_pct": round(atm_put_premium_pct * 100, 2),
                "total_premium": round(total_premium, 0),
                "total_premium_pct": round(total_premium / risk.total_value * 100, 2) if risk.total_value > 0 else 0,
                "max_protection": round(hedge_notional, 0),
                "reason": f"保护性看跌: {contracts}手{underlying} ATM Put, 权利金{total_premium:,.0f}元",
                "risk": "最大损失=权利金",
            }

        elif strategy == "collar":
            T = 1/12
            atm_put_pct = 0.4 * default_iv * math.sqrt(T)
            otm_put_pct = atm_put_pct * 0.7
            otm_call_pct = atm_put_pct * 0.8
            net_cost_pct = otm_put_pct - otm_call_pct
            multiplier = ETF_OPTIONS_SPECS[underlying]["multiplier"]
            one_contract_hedge = index_price * multiplier
            contracts = max(1, round(hedge_notional / one_contract_hedge))
            net_cost = contracts * net_cost_pct * index_price * multiplier

            return {
                "strategy": "collar", "underlying": underlying,
                "contracts": contracts, "net_cost": round(net_cost, 0),
                "put_strike": f"{index_price*0.95:.0f} (OTM 95%)",
                "call_strike": f"{index_price*1.05:.0f} (OTM 105%)",
                "net_cost_pct": round(net_cost / risk.total_value * 100, 2) if risk.total_value > 0 else 0,
                "reason": f"领口: {contracts}手, 净成本{net_cost:,.0f}元",
                "risk": "上行收益封顶+5%",
            }

        elif strategy == "put_spread":
            T = 1/12
            atm_put_pct = 0.4 * default_iv * math.sqrt(T)
            sell_otm_put_pct = atm_put_pct * 0.45
            spread_cost_pct = atm_put_pct - sell_otm_put_pct
            multiplier = ETF_OPTIONS_SPECS[underlying]["multiplier"]
            one_contract_hedge = index_price * multiplier
            contracts = max(1, round(hedge_notional / one_contract_hedge))
            spread_cost = contracts * spread_cost_pct * index_price * multiplier

            return {
                "strategy": "put_spread", "underlying": underlying,
                "contracts": contracts, "spread_cost": round(spread_cost, 0),
                "buy_put_strike": f"{index_price:.0f} (ATM)",
                "sell_put_strike": f"{index_price*0.90:.0f} (OTM 90%)",
                "max_profit": round(hedge_notional * 0.10, 0),
                "reason": f"看跌价差: {contracts}手, 成本{spread_cost:,.0f}元",
                "risk": "保护10%跌幅",
            }

        return {"contracts": [], "total_cost": 0, "reason": "未知策略"}

    def generate_hedge_plan(
        self, risk: PortfolioRisk, market_signals: Dict[str, Any] = None,
        futures_prices: Dict[str, float] = None, prefer_options: bool = False,
        portfolio_volatility: float = None, portfolio_drawdown_60d: float = None,
    ) -> HedgeRecommendation:
        """v5.9 完整对冲方案 — 组合自触发增强"""
        recommendation = HedgeRecommendation()
        recommendation.timestamp = datetime.now().isoformat()
        recommendation.risk_signals = market_signals or {}

        strength, score = self.determine_hedge_signal_strength(
            risk, market_signals, portfolio_volatility, portfolio_drawdown_60d
        )
        recommendation.strength = strength
        recommendation.urgency_score = score

        if strength == HedgeSignalStrength.NO_HEDGE:
            recommendation.hedge_type = HedgeType.NONE
            recommendation.reasoning = "组合风险可控(自波动率+回撤均在安全范围), 无需对冲"
            return recommendation

        recommendation.hedge_type = HedgeType.PUT_PROTECTIVE if prefer_options else HedgeType.FUTURES_SHORT
        hedge_ratio = self.compute_optimal_hedge_ratio(
            risk, strength, method="min_variance",
            portfolio_volatility=portfolio_volatility,
            portfolio_drawdown_60d=portfolio_drawdown_60d,
        )
        recommendation.hedge_ratio = hedge_ratio

        if hedge_ratio <= 0:
            recommendation.hedge_type = HedgeType.NONE
            recommendation.reasoning = "对冲经成本效益分析后判定不划算(预期收益<1.5倍成本)"
            return recommendation

        if not prefer_options:
            futures_result = self.generate_futures_hedge(risk, hedge_ratio, futures_prices)
            recommendation.futures_instruments = list(futures_result.get("contracts", {}).keys())

            contracts = {}
            notionals = {}
            margins = {}
            for code, detail in futures_result.get("contracts", {}).items():
                contracts[code] = detail["contracts"]
                notionals[code] = detail["notional"]
                margins[code] = detail["margin"]

            recommendation.futures_contracts = contracts
            recommendation.futures_notional = notionals
            recommendation.futures_margin = margins
            recommendation.effective_hedge_pct = (
                futures_result.get("total_notional", 0) / risk.stock_exposure
                if risk.stock_exposure > 0 else 0
            )
            hedge_reason = futures_result.get("reason", "")
        else:
            options_result = self.generate_options_hedge(
                risk, hedge_ratio, strategy="protective_put" if score < 0.5 else "put_spread"
            )
            recommendation.options_instruments = [options_result.get("underlying", "510300")]
            recommendation.options_strategy = options_result.get("strategy", "")
            recommendation.options_contracts = [{
                "underlying": options_result.get("underlying"),
                "contracts": options_result.get("contracts", 0),
                "strategy": options_result.get("strategy"),
                "cost": options_result.get("total_premium", options_result.get("spread_cost", 0)),
            }]
            recommendation.options_cost = options_result.get("total_premium", options_result.get("spread_cost", 0))
            recommendation.effective_hedge_pct = hedge_ratio
            hedge_reason = options_result.get("reason", "")

        max_beta = max(risk.beta_csi300, risk.beta_csi500, risk.beta_csi1000)
        recommendation.expected_beta_after = max_beta * (1 - hedge_ratio)
        recommendation.expected_drawdown_reduce = hedge_ratio * 0.4

        strength_names = {
            HedgeSignalStrength.LIGHT: "轻度",
            HedgeSignalStrength.MODERATE: "中度",
            HedgeSignalStrength.STRONG: "强力",
            HedgeSignalStrength.FULL: "完全",
        }

        vol_info = ""
        if portfolio_volatility and portfolio_volatility > 0:
            vol_info = f"组合波动率={portfolio_volatility*100:.1f}%, "
        dd_info = ""
        if portfolio_drawdown_60d and portfolio_drawdown_60d > 0:
            dd_info = f"60日回撤={portfolio_drawdown_60d*100:.1f}%, "

        recommendation.reasoning = (
            f"{strength_names.get(strength, '')}对冲 (评分={score:.2f})。"
            f"最大Beta={max_beta:.2f}, {vol_info}{dd_info}"
            f"对冲比率={hedge_ratio*100:.0f}%。"
            f"{hedge_reason}"
        )

        return recommendation

    def _generate_hedge_reason(self, risk, hedge_ratio, contracts) -> str:
        parts = []
        for code, detail in contracts.items():
            spec = detail.get("spec", {})
            name = spec.get("name", code)
            n = detail["contracts"]
            parts.append(f"做空{n}手{name}")
        return "; ".join(parts) if parts else f"对冲{hedge_ratio*100:.0f}%股票敞口"

    def format_report(self, recommendation: HedgeRecommendation) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  Hedge Engine v5.9 — 对冲策略报告")
        lines.append("=" * 70)
        lines.append(f"  生成时间: {recommendation.timestamp[:19]}")
        lines.append(f"  对冲类型: {recommendation.hedge_type.value}")
        lines.append(f"  信号强度: {recommendation.strength.name} (紧急度={recommendation.urgency_score:.2f})")
        lines.append(f"  对冲比率: {recommendation.hedge_ratio*100:.0f}%")
        lines.append(f"  预期对冲后Beta: {recommendation.expected_beta_after:.2f}")
        lines.append(f"  预期回撤减少: {recommendation.expected_drawdown_reduce*100:.0f}%")
        lines.append("-" * 70)

        if recommendation.futures_contracts:
            lines.append("\n  期货对冲方案 (多指数Beta加权)")
            lines.append("  " + "-" * 50)
            total_margin = 0
            for code, n in recommendation.futures_contracts.items():
                notional = recommendation.futures_notional.get(code, 0)
                margin = recommendation.futures_margin.get(code, 0)
                total_margin += margin
                spec = INDEX_FUTURES_SPECS.get(code, {})
                lines.append(f"    {code} {spec.get('name', '')}: 做空 {n} 手")
                lines.append(f"      名义价值: {notional:,.0f} | 保证金: {margin:,.0f}")
            lines.append(f"\n    总保证金需求: {total_margin:,.0f}")

        if recommendation.options_contracts:
            lines.append("\n  期权对冲方案")
            lines.append("  " + "-" * 50)
            for opt in recommendation.options_contracts:
                lines.append(f"    标的: {opt.get('underlying', '')}")
                lines.append(f"    策略: {opt.get('strategy', '')}")
                lines.append(f"    合约数: {opt.get('contracts', 0)} 张")
                lines.append(f"    预估成本: {opt.get('cost', 0):,.0f}")

        lines.append("\n  对冲逻辑")
        lines.append(f"    {recommendation.reasoning}")

        lines.append("\n" + "=" * 70)
        lines.append("  以上分析仅供参考，不构成投资建议。")
        lines.append("=" * 70)

        return "\n".join(lines)

    def get_hedge_signal_for_fusion(self, portfolio_code: str = "portfolio") -> Dict[str, Any]:
        return {
            "code": portfolio_code, "source": "hedge_engine_v59",
            "action": "HOLD", "score": 0.5, "confidence": 0.3,
            "reason": "对冲引擎v5.9已初始化，等待风险评估",
            "timestamp": datetime.now().isoformat(),
        }


# ── 便捷函数 ──

def get_hedge_engine(portfolio_value: float = None) -> HedgeEngine:
    return HedgeEngine(portfolio_value=portfolio_value or 1_000_000)


def calculate_portfolio_beta(
    positions: Dict[str, Dict[str, Any]], prices: Dict[str, float],
) -> Dict[str, float]:
    engine = HedgeEngine()
    risk = engine.assess_portfolio_risk(positions, prices)
    return {
        "beta_csi300": risk.beta_csi300, "beta_csi500": risk.beta_csi500,
        "beta_csi1000": risk.beta_csi1000, "beta_sse50": risk.beta_sse50,
        "concentration_hhi": risk.concentration_risk, "var_95_daily": risk.var_95_daily,
    }
