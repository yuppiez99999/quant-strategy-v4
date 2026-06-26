# -*- coding: utf-8 -*-
"""
宏观经济决策集成模块 v1.0

将宏观经济量化系统作为量化策略系统的决策方式之一
提供：
  1. 宏观经济信号 → 股票/ETF 仓位调整建议
  2. 期货交易机会 → 期货仓位建议
  3. 综合决策（股票+期货） → 投资组合再平衡建议

集成入口：
    from quant_modules.macro_decision_bridge import MacroDecisionBridge
    bridge = MacroDecisionBridge()
    decision = bridge.get_decision()
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

logger = logging.getLogger('macro_decision_bridge')


# ============================================================
# 决策数据类
# ============================================================

@dataclass
class MacroDecision:
    """宏观经济决策建议"""
    decision_type: str          # stock / futures / portfolio
    action: str                 # BUY / SELL / HOLD / REDUCE / INCREASE
    target: str                 # 标的代码或名称
    target_name: str            # 标的中文名
    confidence: float           # 置信度 0-100
    weight_change: float        # 权重调整建议（+/-）
    reason: str                 # 决策理由
    macro_signals: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


# ============================================================
# 宏观经济决策桥接器
# ============================================================

class MacroDecisionBridge:
    """宏观经济决策桥接器 — 将宏观信号转换为可执行的交易决策"""

    def __init__(self, use_wind: bool = True, use_glm5: bool = True):
        self.use_wind = use_wind
        self.use_glm5 = use_glm5

        # 延迟导入避免循环依赖
        self._analyzer = None
        self._glm5_client = None

        logger.info("MacroDecisionBridge 初始化完成")

    @property
    def analyzer(self):
        """延迟初始化期货机会分析器"""
        if self._analyzer is None:
            try:
                from quant_modules.futures_opportunity_analyzer import FuturesOpportunityAnalyzer
                self._analyzer = FuturesOpportunityAnalyzer(
                    use_wind=self.use_wind, use_glm5=self.use_glm5
                )
            except Exception as e:
                logger.error(f"分析器初始化失败: {e}")
        return self._analyzer

    @property
    def glm5_client(self):
        """延迟初始化 GLM5 客户端"""
        if self._glm5_client is None and self.use_glm5:
            try:
                from utils.glm5_client import GLM5Client
                self._glm5_client = GLM5Client(mode="api")
            except Exception as e:
                logger.warning(f"GLM5 初始化失败: {e}")
        return self._glm5_client

    def get_decision(self) -> Dict[str, Any]:
        """获取综合决策建议"""
        print("\n" + "=" * 60)
        print("🎯 宏观经济决策桥接器启动")
        print("=" * 60)

        # 1. 获取宏观经济数据
        macro_data = self._fetch_macro_data()
        real_economy = self._fetch_real_economy()

        # 2. 生成股票/ETF 决策
        stock_decisions = self._generate_stock_decisions(macro_data, real_economy)

        # 3. 生成期货决策
        futures_decisions = self._generate_futures_decisions()

        # 4. 生成投资组合决策
        portfolio_decision = self._generate_portfolio_decision(
            macro_data, stock_decisions, futures_decisions
        )

        # 5. GLM5 综合分析
        glm5_summary = self._glm5_summary(
            macro_data, stock_decisions, futures_decisions, portfolio_decision
        )

        return {
            'timestamp': datetime.now().isoformat(),
            'macro_data': macro_data,
            'real_economy': real_economy,
            'stock_decisions': [asdict(d) for d in stock_decisions],
            'futures_decisions': [asdict(d) for d in futures_decisions],
            'portfolio_decision': asdict(portfolio_decision) if portfolio_decision else None,
            'glm5_summary': glm5_summary,
        }

    def _fetch_macro_data(self) -> Dict[str, float]:
        """获取宏观经济数据"""
        try:
            from quant_modules.macro_wind_adapter import fetch_macro_data_via_wind
            return fetch_macro_data_via_wind() if self.use_wind else {}
        except Exception as e:
            logger.error(f"获取宏观数据失败: {e}")
            return {}

    def _fetch_real_economy(self) -> Dict[str, Dict[str, float]]:
        """获取实体经济数据"""
        try:
            from quant_modules.macro_wind_adapter import fetch_real_economy_via_wind
            return fetch_real_economy_via_wind() if self.use_wind else {}
        except Exception as e:
            logger.error(f"获取实体经济数据失败: {e}")
            return {}

    def _generate_stock_decisions(
        self, macro_data: Dict, real_economy: Dict
    ) -> List[MacroDecision]:
        """生成股票/ETF 决策建议"""
        decisions = []

        # 基于 PMI
        pmi = macro_data.get('pmi', 50)
        if pmi >= 51:
            decisions.append(MacroDecision(
                decision_type='stock',
                action='INCREASE',
                target='510300',
                target_name='沪深300ETF',
                confidence=min(100, (pmi - 50) * 20),
                weight_change=0.05,
                reason=f"PMI={pmi:.1f}，制造业扩张，利多大盘股",
                macro_signals={'pmi': pmi},
                timestamp=datetime.now().isoformat(),
            ))
        elif pmi <= 49:
            decisions.append(MacroDecision(
                decision_type='stock',
                action='REDUCE',
                target='510300',
                target_name='沪深300ETF',
                confidence=min(100, (50 - pmi) * 20),
                weight_change=-0.05,
                reason=f"PMI={pmi:.1f}，制造业收缩，减仓大盘股",
                macro_signals={'pmi': pmi},
                timestamp=datetime.now().isoformat(),
            ))

        # 基于 CPI
        cpi = macro_data.get('cpi', 0)
        if cpi >= 3.0:
            decisions.append(MacroDecision(
                decision_type='stock',
                action='INCREASE',
                target='518880',
                target_name='黄金ETF',
                confidence=min(100, (cpi - 3) * 30 + 50),
                weight_change=0.03,
                reason=f"CPI={cpi:.1f}%，通胀升温，增配黄金避险",
                macro_signals={'cpi': cpi},
                timestamp=datetime.now().isoformat(),
            ))

        # 基于 PPI
        ppi = macro_data.get('ppi', 0)
        if ppi > 2:
            decisions.append(MacroDecision(
                decision_type='stock',
                action='INCREASE',
                target='601088',
                target_name='中国神华',
                confidence=60,
                weight_change=0.02,
                reason=f"PPI={ppi:.1f}%，工业品涨价，利多资源股",
                macro_signals={'ppi': ppi},
                timestamp=datetime.now().isoformat(),
            ))

        # 基于 M2
        m2 = macro_data.get('m2', 8)
        if m2 >= 10:
            decisions.append(MacroDecision(
                decision_type='stock',
                action='INCREASE',
                target='588000',
                target_name='科创50ETF',
                confidence=55,
                weight_change=0.03,
                reason=f"M2={m2:.1f}%，流动性宽松，利多成长股",
                macro_signals={'m2': m2},
                timestamp=datetime.now().isoformat(),
            ))

        # 基于实体经济指标（螺纹钢 → 周期股）
        rebar_data = real_economy.get('rebar', {})
        if rebar_data:
            current = rebar_data.get('current', 0)
            avg = rebar_data.get('avg', 0)
            if current > avg * 1.05:
                decisions.append(MacroDecision(
                    decision_type='stock',
                    action='INCREASE',
                    target='601088',
                    target_name='中国神华',
                    confidence=65,
                    weight_change=0.02,
                    reason=f"螺纹钢价格 {current:.0f} 高于均值 {avg:.0f}，周期股受益",
                    macro_signals={'rebar_current': current, 'rebar_avg': avg},
                    timestamp=datetime.now().isoformat(),
                ))

        return decisions

    def _generate_futures_decisions(self) -> List[MacroDecision]:
        """生成期货决策建议"""
        decisions = []

        if not self.analyzer:
            return decisions

        try:
            # 调用期货机会分析器
            report = self.analyzer.analyze()
            opportunities = report.get('opportunities', [])

            for opp in opportunities[:3]:  # 取前3个
                action = 'BUY' if opp['direction'] == 'LONG' else ('SELL' if opp['direction'] == 'SHORT' else 'HOLD')
                decisions.append(MacroDecision(
                    decision_type='futures',
                    action=action,
                    target=opp['symbol'],
                    target_name=opp['name'],
                    confidence=opp['confidence'],
                    weight_change=0.1 if action != 'HOLD' else 0,
                    reason=f"综合评分 {opp['signal_strength']:.1f}，宏观 {opp['macro_score']:.1f}，技术 {opp['technical_score']:.1f}",
                    macro_signals={
                        'entry_price': opp['entry_price'],
                        'stop_loss': opp['stop_loss'],
                        'take_profit': opp['take_profit'],
                        'reasons': opp['reasons'],
                    },
                    timestamp=datetime.now().isoformat(),
                ))
        except Exception as e:
            logger.error(f"期货决策生成失败: {e}")

        return decisions

    def _generate_portfolio_decision(
        self,
        macro_data: Dict,
        stock_decisions: List[MacroDecision],
        futures_decisions: List[MacroDecision]
    ) -> Optional[MacroDecision]:
        """生成投资组合层面的决策"""
        # 综合评分
        pmi = macro_data.get('pmi', 50)
        cpi = macro_data.get('cpi', 0)
        m2 = macro_data.get('m2', 8)

        # 简化评分：PMI>50 +1, CPI<3 +1, M2>10 +1
        score = 0
        if pmi > 50: score += 1
        if cpi < 3: score += 1
        if m2 > 10: score += 1

        if score >= 2:
            action = 'INCREASE'
            weight_change = 0.05
            reason = f"宏观环境偏多（PMI={pmi:.1f}, CPI={cpi:.1f}%, M2={m2:.1f}%），建议提升权益仓位"
        elif score <= 0:
            action = 'REDUCE'
            weight_change = -0.05
            reason = f"宏观环境偏空（PMI={pmi:.1f}, CPI={cpi:.1f}%, M2={m2:.1f}%），建议降低权益仓位"
        else:
            action = 'HOLD'
            weight_change = 0
            reason = f"宏观环境中性（PMI={pmi:.1f}, CPI={cpi:.1f}%, M2={m2:.1f}%），维持当前仓位"

        return MacroDecision(
            decision_type='portfolio',
            action=action,
            target='PORTFOLIO',
            target_name='投资组合',
            confidence=abs(score - 1) * 50,
            weight_change=weight_change,
            reason=reason,
            macro_signals={'pmi': pmi, 'cpi': cpi, 'm2': m2, 'score': score},
            timestamp=datetime.now().isoformat(),
        )

    def _glm5_summary(
        self,
        macro_data: Dict,
        stock_decisions: List[MacroDecision],
        futures_decisions: List[MacroDecision],
        portfolio_decision: Optional[MacroDecision]
    ) -> str:
        """GLM5 综合分析"""
        if not self.glm5_client:
            return "GLM5 分析跳过（无客户端）"

        data = {
            'macro_data': macro_data,
            'stock_decisions': [asdict(d) for d in stock_decisions],
            'futures_decisions': [asdict(d) for d in futures_decisions],
            'portfolio_decision': asdict(portfolio_decision) if portfolio_decision else None,
        }

        prompt = f"""你是一位资深投资顾问，请基于以下宏观经济决策建议，生成投资组合调整的综合分析报告：

【宏观经济数据】
{json.dumps(macro_data, ensure_ascii=False, indent=2)}

【股票/ETF 决策建议】
{json.dumps(data['stock_decisions'], ensure_ascii=False, indent=2)}

【期货决策建议】
{json.dumps(data['futures_decisions'], ensure_ascii=False, indent=2)}

【投资组合决策】
{json.dumps(data['portfolio_decision'], ensure_ascii=False, indent=2)}

请按以下结构输出：

## 📊 宏观经济环境评估
（PMI/CPI/PPI/M2 等指标综合判断）

## 🎯 股票/ETF 仓位调整建议
（针对每个决策的详细分析）

## 💰 期货交易机会
（针对每个机会的入场逻辑和风险点）

## ⚖️ 投资组合再平衡建议
（综合股票+期货的配置建议）

## ⚠️ 风险提示
（需要关注的关键风险点）

## 📋 操作清单
（按优先级排序的操作建议）"""

        try:
            result = self.glm5_client.chat(prompt, temperature=0.4)
            return result.get("content", "GLM5 分析失败")
        except Exception as e:
            logger.error(f"GLM5 综合分析失败: {e}")
            return f"GLM5 综合分析失败: {e}"


# ============================================================
# 快捷入口
# ============================================================

def get_macro_decision(use_wind: bool = True, use_glm5: bool = True) -> Dict[str, Any]:
    """快捷函数：获取宏观经济决策建议"""
    bridge = MacroDecisionBridge(use_wind=use_wind, use_glm5=use_glm5)
    return bridge.get_decision()


if __name__ == "__main__":
    print("=" * 60)
    print("宏观经济决策桥接器 - 测试运行")
    print("=" * 60)

    decision = get_macro_decision(use_wind=True, use_glm5=True)

    # 保存决策
    report_dir = os.path.join(_QUANT_DIR, 'reports')
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(
        report_dir,
        f'macro_decision_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(decision, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ 决策报告已保存: {report_file}")
    print(f"\n📈 股票决策: {len(decision['stock_decisions'])} 条")
    print(f"📈 期货决策: {len(decision['futures_decisions'])} 条")
    if decision['portfolio_decision']:
        print(f"📊 组合决策: {decision['portfolio_decision']['action']}")
