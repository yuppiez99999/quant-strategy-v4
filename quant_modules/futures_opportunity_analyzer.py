# -*- coding: utf-8 -*-
"""
期货交易机会分析器 v1.0

基于宏观经济基本面（来自 Wind MCP）+ 期货技术面（来自 futures_options_scanner）
识别期货交易机会，并使用 GLM5 进行深度分析

分析维度：
  1. 宏观经济信号（PMI/CPI/PPI 等指标对期货品种的影响）
  2. 实体经济指标（纸张/水泥/螺纹钢/铜/铝/白酒 对应期货品种）
  3. 期货技术面（价格趋势/基差/期限结构）
  4. 套利机会（跨期/跨品种/跨市场）
  5. GLM5 综合分析报告

使用方式：
    from quant_modules.futures_opportunity_analyzer import FuturesOpportunityAnalyzer
    analyzer = FuturesOpportunityAnalyzer()
    report = analyzer.analyze()
"""
from __future__ import annotations

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict

# 路径设置
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_QUANT_DIR = os.path.dirname(_THIS_DIR)
if _QUANT_DIR not in sys.path:
    sys.path.insert(0, _QUANT_DIR)

logger = logging.getLogger('futures_opportunity')

# ============================================================
# 导入模块
# ============================================================

try:
    from quant_modules.macro_wind_adapter import MacroWindAdapter
    from quant_modules.futures_options_scanner import (
        scan_futures_market, ALL_FUTURES, MONITOR_FUTURES,
        FuturesQuote, ArbitrageSignal
    )
    _MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"模块导入失败: {e}")
    _MODULES_AVAILABLE = False


# ============================================================
# 宏观经济对期货品种影响映射
# ============================================================

# 宏观指标 → 受影响的期货品种 + 影响方向
MACRO_TO_FUTURES_IMPACT = {
    'pmi': {
        'name': '制造业PMI',
        'impact': {
            'CU': 0.8,   'AL': 0.8,   'ZN': 0.7,   # 有色金属（PMI↑利多）
            'RB': 0.9,   'HC': 0.9,   'I': 0.85,   # 黑色系（PMI↑利多）
            'J': 0.8,    'JM': 0.8,                 # 煤焦
            'M': 0.5,    'Y': 0.4,                  'P': 0.4,   # 农产品
            'TA': 0.6,   'MA': 0.6,                 'PP': 0.6, # 化工
        },
        'direction': 'positive',  # PMI↑ → 期货价格↑
        'threshold': 50,          # 荣枯线
    },
    'cpi': {
        'name': 'CPI同比',
        'impact': {
            'CF': 0.6,  'SR': 0.6,   # 棉花/白糖（CPI↑利多农产品）
            'M': 0.5,   'Y': 0.5,    'P': 0.5,
            'AU': 0.7,                # 黄金（通胀避险）
            'AG': 0.6,
        },
        'direction': 'positive',
        'threshold': 3.0,  # 通胀警戒线
    },
    'ppi': {
        'name': 'PPI同比',
        'impact': {
            'RB': 0.8,  'HC': 0.8,   'I': 0.7,     # 黑色系（PPI↑利多）
            'J': 0.7,   'JM': 0.7,
            'CU': 0.6,  'AL': 0.6,   'ZN': 0.5,
            'TA': 0.6,  'MA': 0.5,                 'PP': 0.5,
        },
        'direction': 'positive',
        'threshold': 0,
    },
    'm2': {
        'name': 'M2同比',
        'impact': {
            'IF': 0.7,  'IC': 0.7,   'IH': 0.6,    # 股指（流动性↑利多）
            'AU': 0.6,  'AG': 0.5,                 # 贵金属
            'RB': 0.4,  'I': 0.4,                  # 黑色系
        },
        'direction': 'positive',
        'threshold': 10,
    },
    '社融': {
        'name': '社融存量同比',
        'impact': {
            'IF': 0.7,  'IC': 0.7,                # 股指
            'RB': 0.6,  'I': 0.6,                 # 黑色系
            'CU': 0.5,  'AL': 0.5,
        },
        'direction': 'positive',
        'threshold': 10,
    },
}


# 实体经济指标 → 对应期货品种
REAL_ECONOMY_TO_FUTURES = {
    'rebar':    ['RB', 'HC', 'I', 'J', 'JM'],     # 螺纹钢 → 黑色系
    'copper':   ['CU'],                            # 铜 → 沪铜
    'aluminum': ['AL'],                            # 铝 → 沪铝
    'cement':   ['RB', 'HC', 'I'],                 # 水泥 → 黑色系
    'paper':    ['CF', 'SR'],                       # 纸张 → 软商品（间接）
    'white_spirit': ['CF', 'SR'],                  # 白酒 → 软商品（间接）
}


# ============================================================
# 交易机会数据类
# ============================================================

@dataclass
class TradingOpportunity:
    """期货交易机会"""
    symbol: str                    # 期货代码
    name: str                      # 期货名称
    direction: str                 # LONG/SHORT/NEUTRAL
    signal_strength: float         # 信号强度 0-100
    confidence: float              # 置信度 0-100
    macro_score: float             # 宏观评分
    technical_score: float         # 技术评分
    fundamental_score: float       # 基本面评分
    entry_price: float             # 建议入场价
    stop_loss: float               # 止损价
    take_profit: float             # 止盈价
    risk_level: str                # LOW/MEDIUM/HIGH
    holding_period: str           # 短期/中期/长期
    reasons: List[str]             # 理由列表
    macro_factors: Dict[str, Any] # 宏观因素详情
    source: str = "macro_fundamental"


# ============================================================
# 期货交易机会分析器
# ============================================================

class FuturesOpportunityAnalyzer:
    """期货交易机会分析器 — 宏观基本面 + 技术面 + GLM5 分析"""

    def __init__(self, use_wind: bool = True, use_glm5: bool = True):
        self.use_wind = use_wind
        self.use_glm5 = use_glm5

        # 初始化数据适配器
        self.macro_adapter = MacroWindAdapter(use_wind=use_wind) if _MODULES_AVAILABLE else None

        # 初始化 GLM5 客户端
        self.glm5_client = None
        if use_glm5:
            try:
                from utils.glm5_client import GLM5Client
                self.glm5_client = GLM5Client(mode="api")
                logger.info("✓ GLM5 客户端初始化成功")
            except Exception as e:
                logger.warning(f"GLM5 初始化失败（将使用规则分析）: {e}")
                self.glm5_client = None

        logger.info("FuturesOpportunityAnalyzer 初始化完成")

    def analyze(self) -> Dict[str, Any]:
        """执行完整分析流程"""
        print("\n" + "=" * 60)
        print("🚀 期货交易机会分析器启动")
        print("=" * 60)

        # 1. 获取宏观经济数据
        print("\n📊 [1/5] 获取宏观经济数据...")
        macro_data = self._fetch_macro_data()
        print(f"   宏观指标: {len(macro_data)} 项")

        # 2. 获取实体经济数据
        print("\n📊 [2/5] 获取实体经济数据...")
        real_economy = self._fetch_real_economy()
        print(f"   实体指标: {len(real_economy)} 项")

        # 3. 扫描期货行情
        print("\n📊 [3/5] 扫描期货行情...")
        futures_quotes = self._scan_futures()
        print(f"   期货品种: {len(futures_quotes)} 个")

        # 4. 识别交易机会
        print("\n📊 [4/5] 识别交易机会...")
        opportunities = self._identify_opportunities(macro_data, real_economy, futures_quotes)
        print(f"   识别机会: {len(opportunities)} 个")

        # 5. GLM5 深度分析
        print("\n📊 [5/5] GLM5 深度分析...")
        glm5_analysis = self._glm5_analyze(opportunities, macro_data, real_economy, futures_quotes)

        # 生成报告
        report = self._generate_report(
            macro_data, real_economy, futures_quotes, opportunities, glm5_analysis
        )

        return report

    def _fetch_macro_data(self) -> Dict[str, float]:
        """获取宏观经济数据"""
        if not self.macro_adapter:
            return {}
        try:
            return self.macro_adapter.fetch_macro_data()
        except Exception as e:
            logger.error(f"获取宏观数据失败: {e}")
            return {}

    def _fetch_real_economy(self) -> Dict[str, Dict[str, float]]:
        """获取实体经济数据"""
        if not self.macro_adapter:
            return {}
        try:
            return self.macro_adapter.fetch_real_economy_data()
        except Exception as e:
            logger.error(f"获取实体经济数据失败: {e}")
            return {}

    def _scan_futures(self) -> Dict[str, Any]:
        """扫描期货行情"""
        if not _MODULES_AVAILABLE:
            return {}
        try:
            return scan_futures_market(use_wind=self.use_wind)
        except Exception as e:
            logger.error(f"扫描期货失败: {e}")
            return {}

    def _identify_opportunities(
        self,
        macro_data: Dict[str, float],
        real_economy: Dict[str, Dict[str, float]],
        futures_quotes: Dict[str, Any]
    ) -> List[TradingOpportunity]:
        """识别交易机会 — 宏观+基本面+技术面综合评分"""
        opportunities = []

        for symbol, quote in futures_quotes.items():
            if not isinstance(quote, FuturesQuote):
                continue

            info = ALL_FUTURES.get(symbol, {})
            if not info:
                continue

            # 1. 宏观评分
            macro_score, macro_factors = self._calc_macro_score(symbol, macro_data)

            # 2. 基本面评分（实体经济指标）
            fund_score, fund_reasons = self._calc_fundamental_score(symbol, real_economy)

            # 3. 技术评分
            tech_score, tech_reasons = self._calc_technical_score(quote)

            # 4. 综合评分
            total_score = macro_score * 0.4 + fund_score * 0.3 + tech_score * 0.3
            direction = 'LONG' if total_score >= 60 else ('SHORT' if total_score <= 40 else 'NEUTRAL')
            confidence = min(100, abs(total_score - 50) * 2)

            # 5. 风险等级
            if confidence >= 80:
                risk_level = 'LOW'
            elif confidence >= 50:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'HIGH'

            # 6. 止损止盈（基于价格波动率）
            price = quote.price
            volatility = abs(quote.change_pct) / 100 + 0.02  # 简化波动率
            if direction == 'LONG':
                entry_price = price
                stop_loss = price * (1 - volatility * 1.5)
                take_profit = price * (1 + volatility * 3)
                holding_period = '中期' if total_score >= 70 else '短期'
            elif direction == 'SHORT':
                entry_price = price
                stop_loss = price * (1 + volatility * 1.5)
                take_profit = price * (1 - volatility * 3)
                holding_period = '中期' if total_score <= 30 else '短期'
            else:
                entry_price = price
                stop_loss = price * (1 - volatility)
                take_profit = price * (1 + volatility * 2)
                holding_period = '观望'

            # 仅保留有信号的（非中性或置信度>30）
            if direction != 'NEUTRAL' or confidence > 30:
                opp = TradingOpportunity(
                    symbol=symbol,
                    name=info.get('name', symbol),
                    direction=direction,
                    signal_strength=round(total_score, 2),
                    confidence=round(confidence, 2),
                    macro_score=round(macro_score, 2),
                    technical_score=round(tech_score, 2),
                    fundamental_score=round(fund_score, 2),
                    entry_price=round(entry_price, 2),
                    stop_loss=round(stop_loss, 2),
                    take_profit=round(take_profit, 2),
                    risk_level=risk_level,
                    holding_period=holding_period,
                    reasons=fund_reasons + tech_reasons,
                    macro_factors=macro_factors,
                )
                opportunities.append(opp)

        # 按信号强度排序
        opportunities.sort(key=lambda x: x.signal_strength, reverse=True)
        return opportunities

    def _calc_macro_score(self, symbol: str, macro_data: Dict[str, float]) -> Tuple[float, Dict]:
        """计算宏观评分"""
        score = 50  # 中性起点
        factors = {}

        for macro_key, impact_cfg in MACRO_TO_FUTURES_IMPACT.items():
            if macro_key not in macro_data:
                continue

            value = macro_data[macro_key]
            threshold = impact_cfg['threshold']
            direction = impact_cfg['direction']
            impact_weight = impact_cfg['impact'].get(symbol, 0)

            if impact_weight == 0:
                continue

            # 计算偏离度
            if direction == 'positive':
                deviation = (value - threshold) / threshold * 100
            else:
                deviation = (threshold - value) / threshold * 100

            # 评分调整（限制在 ±20 内）
            adjustment = max(-20, min(20, deviation * impact_weight))
            score += adjustment

            factors[macro_key] = {
                'name': impact_cfg['name'],
                'value': value,
                'threshold': threshold,
                'impact_weight': impact_weight,
                'adjustment': round(adjustment, 2)
            }

        return max(0, min(100, score)), factors

    def _calc_fundamental_score(self, symbol: str, real_economy: Dict) -> Tuple[float, List[str]]:
        """计算基本面评分（基于实体经济指标）"""
        score = 50
        reasons = []

        for re_key, related_symbols in REAL_ECONOMY_TO_FUTURES.items():
            if symbol not in related_symbols:
                continue

            if re_key not in real_economy:
                continue

            item = real_economy[re_key]
            current = item.get('current', 0)
            avg = item.get('avg', 0)
            std = item.get('std', 1)

            if std == 0:
                continue

            # Z-score
            z_score = (current - avg) / std
            # 评分调整：高于均值利多，低于均值利空
            adjustment = max(-15, min(15, z_score * 10))
            score += adjustment

            if z_score > 0.5:
                reasons.append(f"{item.get('name', re_key)}价格高于均值（Z={z_score:.2f}），利多")
            elif z_score < -0.5:
                reasons.append(f"{item.get('name', re_key)}价格低于均值（Z={z_score:.2f}），利空")

        return max(0, min(100, score)), reasons

    def _calc_technical_score(self, quote: FuturesQuote) -> Tuple[float, List[str]]:
        """计算技术评分"""
        score = 50
        reasons = []

        # 涨跌幅
        change = quote.change_pct
        if change > 2:
            score += 15
            reasons.append(f"强势上涨 {change:+.2f}%")
        elif change > 0.5:
            score += 8
            reasons.append(f"温和上涨 {change:+.2f}%")
        elif change < -2:
            score -= 15
            reasons.append(f"强势下跌 {change:+.2f}%")
        elif change < -0.5:
            score -= 8
            reasons.append(f"温和下跌 {change:+.2f}%")

        # 成交量（简化判断）
        if hasattr(quote, 'volume') and quote.volume > 0:
            if quote.volume > 100000:  # 高活跃度
                score += 5
                reasons.append("成交活跃")

        return max(0, min(100, score)), reasons

    def _glm5_analyze(
        self,
        opportunities: List[TradingOpportunity],
        macro_data: Dict,
        real_economy: Dict,
        futures_quotes: Dict
    ) -> str:
        """使用 GLM5 进行深度分析"""
        if not self.glm5_client or not opportunities:
            return "GLM5 分析跳过（无客户端或无机会）"

        # 准备分析数据
        top_opps = opportunities[:5]  # 取前5个机会
        analysis_data = {
            "timestamp": datetime.now().isoformat(),
            "macro_indicators": macro_data,
            "real_economy": {
                k: {"current": v.get("current"), "avg": v.get("avg"), "name": v.get("name")}
                for k, v in real_economy.items()
            },
            "top_opportunities": [
                {
                    "symbol": o.symbol,
                    "name": o.name,
                    "direction": o.direction,
                    "signal_strength": o.signal_strength,
                    "macro_score": o.macro_score,
                    "fundamental_score": o.fundamental_score,
                    "technical_score": o.technical_score,
                    "entry_price": o.entry_price,
                    "stop_loss": o.stop_loss,
                    "take_profit": o.take_profit,
                    "reasons": o.reasons,
                }
                for o in top_opps
            ],
        }

        prompt = f"""你是一位资深期货交易分析师，请基于以下数据进行期货交易机会深度分析：

【宏观经济指标】
{json.dumps(macro_data, ensure_ascii=False, indent=2)}

【实体经济指标】
{json.dumps(analysis_data['real_economy'], ensure_ascii=False, indent=2)}

【识别的交易机会（Top 5）】
{json.dumps(analysis_data['top_opportunities'], ensure_ascii=False, indent=2)}

请按以下结构输出分析报告：

## 📊 宏观经济环境评估
（PMI/CPI/PPI/M2/社融对期货市场的影响）

## 🏭 实体经济基本面分析
（纸张/水泥/螺纹钢/铜/铝等指标的信号）

## 🎯 重点期货品种机会分析
（针对每个 Top 5 机会，分析：）
- 基本面驱动因素
- 技术面信号确认
- 入场逻辑
- 风险点
- 仓位建议（占总资金比例）

## ⚠️ 风险提示
（宏观风险、政策风险、流动性风险）

## 📋 操作建议汇总
（按优先级排序的交易计划）"""

        try:
            result = self.glm5_client.chat(prompt, temperature=0.4)
            return result.get("content", "GLM5 分析失败")
        except Exception as e:
            logger.error(f"GLM5 分析失败: {e}")
            return f"GLM5 分析失败: {e}"

    def _generate_report(
        self,
        macro_data: Dict,
        real_economy: Dict,
        futures_quotes: Dict,
        opportunities: List[TradingOpportunity],
        glm5_analysis: str
    ) -> Dict[str, Any]:
        """生成完整报告"""
        return {
            'timestamp': datetime.now().isoformat(),
            'data_source': 'wind_mcp' if self.use_wind else 'default',
            'macro_data': macro_data,
            'real_economy': {
                k: {'current': v.get('current'), 'avg': v.get('avg'), 'name': v.get('name')}
                for k, v in real_economy.items()
            },
            'futures_quotes': {
                sym: {
                    'name': q.name,
                    'price': q.price,
                    'change_pct': q.change_pct,
                    'volume': q.volume,
                    'source': q.source,
                }
                for sym, q in futures_quotes.items() if isinstance(q, FuturesQuote)
            },
            'opportunities': [asdict(o) for o in opportunities],
            'glm5_analysis': glm5_analysis,
            'summary': {
                'total_opportunities': len(opportunities),
                'long_signals': len([o for o in opportunities if o.direction == 'LONG']),
                'short_signals': len([o for o in opportunities if o.direction == 'SHORT']),
                'neutral': len([o for o in opportunities if o.direction == 'NEUTRAL']),
                'top_pick': opportunities[0].symbol if opportunities else None,
            }
        }


# ============================================================
# 快捷入口
# ============================================================

def analyze_futures_opportunities(use_wind: bool = True, use_glm5: bool = True) -> Dict[str, Any]:
    """快捷函数：分析期货交易机会"""
    analyzer = FuturesOpportunityAnalyzer(use_wind=use_wind, use_glm5=use_glm5)
    return analyzer.analyze()


if __name__ == "__main__":
    print("=" * 60)
    print("期货交易机会分析器 - 测试运行")
    print("=" * 60)

    report = analyze_futures_opportunities(use_wind=True, use_glm5=True)

    # 保存报告
    report_dir = os.path.join(_QUANT_DIR, 'reports')
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, f'futures_opportunity_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ 报告已保存: {report_file}")
    print(f"\n📈 识别机会: {report['summary']['total_opportunities']} 个")
    print(f"   多头信号: {report['summary']['long_signals']}")
    print(f"   空头信号: {report['summary']['short_signals']}")
    print(f"   首选品种: {report['summary']['top_pick']}")
