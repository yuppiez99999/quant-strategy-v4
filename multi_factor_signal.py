# -*- coding: utf-8 -*-
"""
多因子信号生成器
融合: YiZhao事件驱动因子 + 双均线技术因子 + 因子权重回测优化

模块5 对应 research_plan_yizhao_optimization.md:
  - 新增因子: 舆情情绪因子、事件冲击因子、文本热度因子
  - 与现有双均线因子融合
  - 因子权重通过回测优化
"""
import os
import sys
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from event_driven_factor import EventDrivenFactor, get_factor_generator
from fin_sentiment_analyzer import FinSentimentAnalyzer, get_sentiment_analyzer
from yizhao_data_loader import YiZhaoDataLoader, get_yizhao_loader


# ============================================================
# 技术因子: 双均线 + MACD + RSI
# ============================================================
class TechnicalFactor:
    """经典技术指标因子生成器"""

    def __init__(self):
        self._price_cache: Dict[str, List[float]] = defaultdict(list)
        self._window = 60  # 默认缓存60日价格

    def update_price(self, code: str, price: float):
        """更新价格序列"""
        seq = self._price_cache[code]
        seq.append(price)
        if len(seq) > self._window * 2:
            self._price_cache[code] = seq[-self._window:]

    def batch_load_prices(self, prices: Dict[str, List[float]]):
        """批量加载历史价格数据 {code: [p1, p2, ...]}"""
        for code, seq in prices.items():
            self._price_cache[code] = list(seq)[-self._window:]

    def sma(self, data: List[float], period: int) -> float:
        """简单移动平均"""
        if len(data) < period:
            return data[-1] if data else 0
        return sum(data[-period:]) / period

    def ema(self, data: List[float], period: int) -> float:
        """指数移动平均"""
        if len(data) < 2:
            return data[-1] if data else 0
        multiplier = 2 / (period + 1)
        ema_val = data[0]
        for price in data[1:]:
            ema_val = (price - ema_val) * multiplier + ema_val
        return ema_val

    def dual_ma_factor(self, code: str, short_period: int = 12,
                       long_period: int = 26) -> float:
        """
        双均线因子
        SMA(short) vs SMA(long)
        范围: [-1, 1]
        正值: 多头排列(短均线 > 长均线)
        负值: 空头排列
        """
        prices = self._price_cache.get(code, [])
        if len(prices) < long_period:
            return 0.0

        short_ma = self.sma(prices, short_period)
        long_ma = self.sma(prices, long_period)
        if long_ma == 0:
            return 0.0

        # 金叉/死叉偏离度
        deviation = (short_ma - long_ma) / long_ma
        # 映射到 [-1, 1], 5%偏离→±1
        factor = np.clip(deviation * 20, -1, 1)
        return round(float(factor), 4)

    def macd_factor(self, code: str,
                    fast: int = 12, slow: int = 26, signal: int = 9) -> float:
        """
        MACD 因子
        DIFF 与 DEA 之差归一化
        """
        prices = self._price_cache.get(code, [])
        if len(prices) < slow + signal:
            return 0.0

        ema_fast = self.ema(prices, fast)
        ema_slow = self.ema(prices, slow)
        diff = ema_fast - ema_slow

        # 简化 DEA = diff 的 signal 周期 SMA
        # 此处简化: 直接用 diff / 价格 归一化
        current_price = prices[-1] if prices else 1
        if current_price == 0:
            return 0.0

        macd_val = diff / current_price
        factor = np.clip(macd_val * 100, -1, 1)
        return round(float(factor), 4)

    def rsi_factor(self, code: str, period: int = 14) -> float:
        """RSI 因子: 映射 [0,100] → [-1,1]"""
        prices = self._price_cache.get(code, [])
        if len(prices) < period + 1:
            return 0.0

        gains = []
        losses = []
        for i in range(-period, 0):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # RSI: 70→+0.5, 50→0, 30→-0.5
        factor = (rsi - 50) / 40
        return round(float(np.clip(factor, -1, 1)), 4)

    def composite_technical(self, code: str) -> Dict[str, float]:
        """综合技术因子"""
        return {
            'dual_ma': self.dual_ma_factor(code),
            'macd': self.macd_factor(code),
            'rsi': self.rsi_factor(code)
        }


# ============================================================
# 多因子信号生成器
# ============================================================
class MultiFactorSignal:
    """
    多因子融合信号生成器
    因子库:
      事件驱动类 (YiZhao):
        - sentiment:    舆情情绪因子
        - event_impact: 事件冲击因子
        - text_heat:    文本热度因子
        - industry_corr:行业联动因子
        - policy_bias:  政策倾向因子
      技术类:
        - dual_ma:      双均线因子
        - macd:         MACD 因子
        - rsi:          RSI 因子
    """

    # 默认权重: 事件驱动 60% + 技术 40%
    DEFAULT_WEIGHTS = {
        'sentiment': 0.18,
        'event_impact': 0.14,
        'text_heat': 0.08,
        'industry_corr': 0.08,
        'policy_bias': 0.12,
        'dual_ma': 0.16,
        'macd': 0.12,
        'rsi': 0.12
    }

    SIGNAL_THRESHOLDS = {
        'strong_buy': 0.30,
        'buy': 0.10,
        'hold_upper': 0.10,
        'hold_lower': -0.10,
        'sell': -0.10,
        'strong_sell': -0.30
    }

    def __init__(self,
                 event_factor: EventDrivenFactor = None,
                 tech_factor: TechnicalFactor = None,
                 weights: Dict[str, float] = None):
        self.event_factor = event_factor or get_factor_generator()
        self.tech_factor = tech_factor or TechnicalFactor()
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)

        # 信号缓存
        self._signal_cache: Dict[str, Dict] = {}
        self._signal_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=60)
        )

    def load_historical_prices(self, prices: Dict[str, List[float]]):
        """加载历史价格数据用于技术因子计算"""
        self.tech_factor.batch_load_prices(prices)

    def update_price(self, code: str, price: float):
        """更新单只标的价格"""
        self.tech_factor.update_price(code, price)

    def compute_all_factors(self, code: str) -> Dict[str, float]:
        """计算所有因子值"""
        factors = {}

        # 事件驱动因子
        try:
            event_result = self.event_factor.compute_composite_factor(code)
            factors.update(event_result.get('factors', {}))
        except Exception:
            for name in ['sentiment', 'event_impact', 'text_heat',
                         'industry_corr', 'policy_bias']:
                factors[name] = 0.0

        # 技术因子
        try:
            tech = self.tech_factor.composite_technical(code)
            factors.update(tech)
        except Exception:
            for name in ['dual_ma', 'macd', 'rsi']:
                factors[name] = 0.0

        return factors

    def compute_composite_signal(self, code: str) -> Dict:
        """
        计算综合多因子信号
        返回:
          {'code': str, 'composite': float, 'signal': str,
           'factors': Dict, 'confidence': float}
        """
        factors = self.compute_all_factors(code)

        # 加权合成
        composite = 0.0
        total_weight = 0.0
        for name, val in factors.items():
            w = self.weights.get(name, 0.0)
            composite += val * w
            total_weight += w

        if total_weight > 0:
            composite = composite / total_weight * sum(self.weights.values())

        # 信号生成
        signal = self._classify_signal(composite)

        # 置信度 (基于因子一致性)
        confidence = self._compute_confidence(factors)

        result = {
            'code': code,
            'composite': round(composite, 4),
            'signal': signal,
            'factors': {k: round(v, 4) for k, v in factors.items()},
            'confidence': round(confidence, 4),
            'timestamp': datetime.now().isoformat()
        }

        self._signal_cache[code] = result
        self._signal_history[code].append(result)

        return result

    def _classify_signal(self, composite: float) -> str:
        thresholds = self.SIGNAL_THRESHOLDS
        if composite >= thresholds['strong_buy']:
            return 'strong_buy'
        elif composite >= thresholds['buy']:
            return 'buy'
        elif composite >= thresholds['hold_lower']:
            return 'hold'
        elif composite >= thresholds['strong_sell']:
            return 'sell'
        else:
            return 'strong_sell'

    def _compute_confidence(self, factors: Dict[str, float]) -> float:
        """
        基于因子一致性的置信度计算
        因子方向越一致, 置信度越高
        """
        signs = []
        for name, val in factors.items():
            if name in ('text_heat',):  # 热度不参与方向判断
                continue
            if abs(val) > 0.05:  # 过滤弱信号
                signs.append(1 if val > 0 else -1)

        if not signs:
            return 0.5

        agreement = sum(1 for s in signs if s == signs[0])
        ratio = agreement / len(signs)
        # 映射到 [0, 1], 一致性=不一致→0.3 基准
        confidence = 0.3 + ratio * 0.7
        return round(confidence, 4)

    def compute_portfolio_signals(self, codes: List[str] = None) -> Dict:
        """计算组合级别多因子信号"""
        if codes is None:
            codes = list(self.event_factor.loader.config.portfolio_keywords.keys())

        results = {}
        all_composites = []
        signal_dist = defaultdict(int)

        for code in codes:
            r = self.compute_composite_signal(code)
            results[code] = r
            all_composites.append(r['composite'])
            signal_dist[r['signal']] += 1

        avg = np.mean(all_composites) if all_composites else 0
        std = np.std(all_composites) if all_composites else 0

        return {
            'portfolio_composite': round(float(avg), 4),
            'composite_std': round(float(std), 4),
            'signal_distribution': dict(signal_dist),
            'code_signals': results,
            'dominant_signal': max(signal_dist, key=signal_dist.get) if signal_dist else 'hold',
            'timestamp': datetime.now().isoformat()
        }

    def get_signal_trend(self, code: str, window: int = 10) -> Dict:
        """获取信号趋势"""
        history = list(self._signal_history.get(code, []))[-window:]
        if len(history) < 2:
            return {'trend': 'flat', 'change': 0.0}

        composites = [h['composite'] for h in history]
        change = composites[-1] - composites[0]

        if change > 0.1:
            trend = 'improving'
        elif change < -0.1:
            trend = 'deteriorating'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'change': round(change, 4),
            'current': composites[-1],
            'window_avg': round(np.mean(composites), 4)
        }


# ============================================================
# 因子权重优化器
# ============================================================
class FactorWeightOptimizer:
    """
    基于历史回测优化因子权重
    方法: 网格搜索 + IC最大化
    """

    def __init__(self, signal_gen: MultiFactorSignal = None):
        self.signal_gen = signal_gen or MultiFactorSignal()

    def grid_search_weights(self,
                            code: str,
                            factor_history: Dict[str, List[float]],
                            future_returns: List[float],
                            step: float = 0.05) -> Dict:
        """
        网格搜索最优因子权重
        目标: 最大化因子值与未来收益的 IC

        参数:
          factor_history: {factor_name: [历史值列表]}
          future_returns:  [对应未来收益列表]
          step: 权重搜索步长
        """
        factor_names = list(factor_history.keys())
        n = len(factor_names)

        # 生成候选权重网格 (归一化到和为1)
        best_ic = -1.0
        best_weights = {name: 1.0 / n for name in factor_names}
        best_config = None

        # 生成权重组合 (使用 product of discretized values)
        grid_values = [round(i * step, 2) for i in range(int(1 / step) + 1)]

        # 对关键因子 (前3个) 做精细搜索, 其余均分剩余
        primary_factors = factor_names[:min(3, n)]
        secondary_factors = factor_names[min(3, n):]

        for combo in product(grid_values, repeat=len(primary_factors)):
            weight_sum = sum(combo)
            if weight_sum > 1.0 or weight_sum < 0.3:
                continue

            # 剩余权重均分给次要因子
            remaining = 1.0 - weight_sum
            if secondary_factors:
                secondary_weight = remaining / len(secondary_factors)
            else:
                secondary_weight = 0

            # 构建完整权重
            weights = {}
            for i, name in enumerate(primary_factors):
                weights[name] = combo[i]
            for name in secondary_factors:
                weights[name] = secondary_weight

            # 计算合成因子值
            composite = np.zeros(len(future_returns))
            for name in factor_names:
                vals = np.array(factor_history[name][:len(future_returns)])
                composite += vals * weights.get(name, 0)

            # 计算 IC
            if len(composite) > 10 and np.std(composite) > 0:
                ic = np.corrcoef(composite, future_returns)[0, 1]
                if not np.isnan(ic):
                    ic_abs = abs(ic)
                    if ic_abs > best_ic:
                        best_ic = ic_abs
                        best_weights = dict(weights)
                        best_config = {
                            'ic': round(float(ic), 4),
                            'ic_abs': round(ic_abs, 4),
                            'weights': best_weights
                        }

        return {
            'best_ic': round(float(best_ic), 4),
            'best_weights': best_weights,
            'optimization_success': best_config is not None,
            'n_combinations_tested': sum(
                1 for combo in product(grid_values, repeat=len(primary_factors))
                if 0.3 <= sum(combo) <= 1.0
            )
        }

    def optimize_and_apply(self, code: str,
                           factor_history: Dict[str, List[float]],
                           future_returns: List[float]) -> Dict:
        """优化并应用新权重"""
        result = self.grid_search_weights(code, factor_history, future_returns)
        if result['optimization_success']:
            self.signal_gen.weights.update(result['best_weights'])
        return result

    def compute_rolling_ic(self, code: str,
                           factor_history: Dict[str, List[float]],
                           future_returns: List[float],
                           window: int = 20) -> List[float]:
        """计算滚动 IC 序列"""
        n = len(future_returns)
        ic_series = []

        for i in range(window, n):
            composite = np.zeros(window)
            for name in factor_history:
                vals = np.array(factor_history[name][i - window:i])
                composite += vals * self.signal_gen.weights.get(name, 0)

            returns = np.array(future_returns[i - window:i])
            if np.std(composite) > 0:
                ic = np.corrcoef(composite, returns)[0, 1]
                ic_series.append(round(float(ic if not np.isnan(ic) else 0), 4))
            else:
                ic_series.append(0.0)

        return ic_series


# ============================================================
# 便捷函数
# ============================================================
_global_signal_gen: Optional[MultiFactorSignal] = None
_global_optimizer: Optional[FactorWeightOptimizer] = None


def get_signal_generator(weights: Dict[str, float] = None) -> MultiFactorSignal:
    """获取全局多因子信号生成器"""
    global _global_signal_gen
    if _global_signal_gen is None:
        _global_signal_gen = MultiFactorSignal(weights=weights)
    elif weights is not None:
        _global_signal_gen.weights.update(weights)
    return _global_signal_gen


def get_weight_optimizer() -> FactorWeightOptimizer:
    """获取全局权重优化器"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = FactorWeightOptimizer()
    return _global_optimizer


# ============================================================
# 测试
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  多因子信号生成器测试")
    print("=" * 60)

    gen = get_signal_generator()

    test_codes = ['601088', '300274', '002371', '600276']

    print("\n  单标的信号:")
    for code in test_codes:
        result = gen.compute_composite_signal(code)
        print(f"\n    {code}:")
        print(f"      综合因子: {result['composite']:.4f}")
        print(f"      信号: {result['signal']}")
        print(f"      置信度: {result['confidence']:.2%}")
        print(f"      因子明细:")
        for name, val in result['factors'].items():
            bar = '█' * int(abs(val) * 15)
            sign = '+' if val > 0 else ' '
            print(f"        {name:>15}: {sign}{val:.4f} {bar}")

    print(f"\n{'=' * 60}")
    print("  组合级别信号")
    print("=" * 60)
    portfolio = gen.compute_portfolio_signals(test_codes)
    print(f"  组合综合因子: {portfolio['portfolio_composite']:.4f}")
    print(f"  主导信号: {portfolio['dominant_signal']}")
    print(f"  信号分布: {portfolio['signal_distribution']}")

    print(f"\n{'=' * 60}")
    print("  权重优化测试 (模拟数据)")
    print("=" * 60)
    np.random.seed(42)
    # 模拟60天因子历史和未来收益
    n_days = 60
    mock_history = {
        'sentiment': np.cumsum(np.random.randn(n_days) * 0.1),
        'event_impact': np.cumsum(np.random.randn(n_days) * 0.08),
        'text_heat': np.random.uniform(0.3, 0.8, n_days),
        'industry_corr': np.random.uniform(0.4, 0.7, n_days),
        'policy_bias': np.random.uniform(0.2, 0.6, n_days),
        'dual_ma': np.cumsum(np.random.randn(n_days) * 0.12),
        'macd': np.cumsum(np.random.randn(n_days) * 0.1),
        'rsi': np.clip(np.cumsum(np.random.randn(n_days) * 0.08), -1, 1),
    }
    mock_returns = np.random.randn(n_days) * 0.02

    optimizer = get_weight_optimizer()
    opt_result = optimizer.grid_search_weights(
        'SIM_TEST', mock_history, mock_returns, step=0.1
    )
    print(f"  最优 IC: {opt_result['best_ic']:.4f}")
    print(f"  最优权重: {opt_result['best_weights']}")
    print(f"  测试组合数: {opt_result['n_combinations_tested']}")
