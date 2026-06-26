# -*- coding: utf-8 -*-
"""
GLM5 期货分析报告生成器 v1.0

独立的可执行脚本，用于：
  1. 调用宏观经济量化系统获取基本面数据
  2. 扫描期货市场获取技术面数据
  3. 使用 GLM5 生成深度分析报告
  4. 输出 Markdown 格式报告

使用方式：
    python generate_glm5_futures_report.py
    python generate_glm5_futures_report.py --no-wind     # 不使用 Wind MCP
    python generate_glm5_futures_report.py --no-glm5     # 不使用 GLM5
"""
from __future__ import annotations

import os
import sys

# 修复 Windows GBK 编码问题
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

# 路径设置
_THIS_FILE = os.path.abspath(__file__)
_THIS_DIR = os.path.dirname(_THIS_FILE)  # 11_量化策略/ (脚本所在目录)
_QUANT_DIR = _THIS_DIR  # quant_modules 就在 11_量化策略/ 下
if _QUANT_DIR not in sys.path:
    sys.path.insert(0, _QUANT_DIR)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(_QUANT_DIR, 'logs', f'glm5_futures_{datetime.now().strftime("%Y%m%d")}.log'),
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)


def generate_report(use_wind: bool = True, use_glm5: bool = True) -> str:
    """生成 GLM5 期货分析报告"""
    print("=" * 60)
    print("🤖 GLM5 期货分析报告生成器")
    print("=" * 60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Wind MCP: {'启用' if use_wind else '禁用'}")
    print(f"GLM5:     {'启用' if use_glm5 else '禁用'}")
    print("=" * 60)

    # 1. 获取期货交易机会分析
    print("\n📊 [1/3] 获取期货交易机会...")
    try:
        from quant_modules.futures_opportunity_analyzer import FuturesOpportunityAnalyzer
        analyzer = FuturesOpportunityAnalyzer(use_wind=use_wind, use_glm5=use_glm5)
        analysis = analyzer.analyze()
    except Exception as e:
        logger.error(f"期货机会分析失败: {e}")
        import traceback
        traceback.print_exc()
        analysis = {'error': str(e), 'opportunities': [], 'glm5_analysis': ''}

    # 2. 获取宏观经济决策
    print("\n📊 [2/3] 获取宏观经济决策...")
    try:
        from quant_modules.macro_decision_bridge import MacroDecisionBridge
        bridge = MacroDecisionBridge(use_wind=use_wind, use_glm5=use_glm5)
        decision = bridge.get_decision()
    except Exception as e:
        logger.error(f"宏观经济决策失败: {e}")
        import traceback
        traceback.print_exc()
        decision = {'error': str(e), 'stock_decisions': [], 'futures_decisions': []}

    # 3. 生成 Markdown 报告
    print("\n📊 [3/3] 生成 Markdown 报告...")
    report_md = _build_markdown_report(analysis, decision)

    # 保存报告
    report_dir = os.path.join(_QUANT_DIR, 'reports')
    os.makedirs(report_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_file = os.path.join(report_dir, f'GLM5_期货分析报告_{timestamp}.md')
    json_file = os.path.join(report_dir, f'GLM5_期货分析报告_{timestamp}.json')

    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(report_md)

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'analysis': analysis,
            'decision': decision,
            'report_file': md_file,
            'timestamp': datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ Markdown 报告: {md_file}")
    print(f"✅ JSON 数据:    {json_file}")

    return md_file


def _build_markdown_report(analysis: dict, decision: dict) -> str:
    """构建 Markdown 报告"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    md = f"""# 🤖 GLM5 期货交易机会分析报告

**生成时间**: {now}
**数据源**: Wind MCP（基本面）+ 期货市场扫描（技术面）+ GLM5（AI分析）

---

## 📊 一、宏观经济环境

"""

    # 宏观经济数据
    macro_data = decision.get('macro_data', {}) or analysis.get('macro_data', {})
    if macro_data:
        md += "| 指标 | 数值 | 信号 |\n|------|------|------|\n"
        for k, v in macro_data.items():
            signal = _get_macro_signal(k, v)
            md += f"| {_get_macro_name(k)} | {v:.2f} | {signal} |\n"
    else:
        md += "宏观数据获取失败\n"

    md += "\n## 🏭 二、实体经济指标\n\n"

    # 实体经济数据
    real_economy = decision.get('real_economy', {}) or analysis.get('real_economy', {})
    if real_economy:
        md += "| 指标 | 当前值 | 均值 | 偏离度 | 信号 |\n|------|--------|------|--------|------|\n"
        for k, v in real_economy.items():
            if isinstance(v, dict):
                current = v.get('current', 0)
                avg = v.get('avg', 0)
                name = v.get('name', k)
                if avg > 0:
                    deviation = (current - avg) / avg * 100
                    signal = "利多" if deviation > 5 else ("利空" if deviation < -5 else "中性")
                else:
                    deviation = 0
                    signal = "中性"
                md += f"| {name} | {current:.2f} | {avg:.2f} | {deviation:+.1f}% | {signal} |\n"
    else:
        md += "实体经济数据获取失败\n"

    md += "\n## 🎯 三、期货交易机会\n\n"

    # 期货交易机会
    opportunities = analysis.get('opportunities', [])
    if opportunities:
        md += "| 排名 | 品种 | 方向 | 信号强度 | 置信度 | 入场价 | 止损 | 止盈 |\n"
        md += "|------|------|------|----------|--------|--------|------|------|\n"
        for i, opp in enumerate(opportunities[:10], 1):
            direction_emoji = "🟢多" if opp['direction'] == 'LONG' else ("🔴空" if opp['direction'] == 'SHORT' else "⚪中性")
            md += (f"| {i} | {opp['name']}({opp['symbol']}) | {direction_emoji} | "
                   f"{opp['signal_strength']:.1f} | {opp['confidence']:.1f} | "
                   f"{opp['entry_price']} | {opp['stop_loss']} | {opp['take_profit']} |\n")

        md += "\n### 机会详情\n\n"
        for i, opp in enumerate(opportunities[:5], 1):
            md += f"#### {i}. {opp['name']}（{opp['symbol']}）\n\n"
            md += f"- **方向**: {opp['direction']}\n"
            md += f"- **综合评分**: {opp['signal_strength']:.1f}/100\n"
            md += f"- **宏观评分**: {opp['macro_score']:.1f}/100\n"
            md += f"- **基本面评分**: {opp['fundamental_score']:.1f}/100\n"
            md += f"- **技术评分**: {opp['technical_score']:.1f}/100\n"
            md += f"- **入场价**: {opp['entry_price']}\n"
            md += f"- **止损价**: {opp['stop_loss']}\n"
            md += f"- **止盈价**: {opp['take_profit']}\n"
            md += f"- **风险等级**: {opp['risk_level']}\n"
            md += f"- **持有周期**: {opp['holding_period']}\n"
            if opp.get('reasons'):
                md += f"- **理由**:\n"
                for r in opp['reasons']:
                    md += f"  - {r}\n"
            md += "\n"
    else:
        md += "未识别到交易机会\n"

    md += "\n## 💼 四、股票/ETF 决策建议\n\n"

    stock_decisions = decision.get('stock_decisions', [])
    if stock_decisions:
        md += "| 标的 | 动作 | 权重调整 | 置信度 | 理由 |\n|------|------|----------|--------|------|\n"
        for d in stock_decisions:
            action_emoji = {"INCREASE": "📈增仓", "REDUCE": "📉减仓", "BUY": "🟢买入",
                          "SELL": "🔴卖出", "HOLD": "⚪持有"}.get(d['action'], d['action'])
            md += f"| {d['target_name']} | {action_emoji} | {d['weight_change']:+.1%} | {d['confidence']:.0f}% | {d['reason']} |\n"
    else:
        md += "无股票/ETF 决策建议\n"

    md += "\n## 📋 五、投资组合决策\n\n"

    portfolio_decision = decision.get('portfolio_decision')
    if portfolio_decision:
        action_emoji = {"INCREASE": "📈增仓", "REDUCE": "📉减仓", "HOLD": "⚪持有"}.get(
            portfolio_decision['action'], portfolio_decision['action']
        )
        md += f"- **动作**: {action_emoji}\n"
        md += f"- **权重调整**: {portfolio_decision['weight_change']:+.1%}\n"
        md += f"- **置信度**: {portfolio_decision['confidence']:.0f}%\n"
        md += f"- **理由**: {portfolio_decision['reason']}\n"
    else:
        md += "无投资组合决策\n"

    md += "\n## 🤖 六、GLM5 深度分析\n\n"

    glm5_analysis = analysis.get('glm5_analysis', '')
    if glm5_analysis:
        md += glm5_analysis
    else:
        md += "GLM5 分析不可用\n"

    md += "\n\n## 🤖 七、GLM5 综合决策分析\n\n"

    glm5_summary = decision.get('glm5_summary', '')
    if glm5_summary:
        md += glm5_summary
    else:
        md += "GLM5 综合分析不可用\n"

    md += f"""

---

## ⚠️ 风险提示

1. **宏观风险**: 经济数据可能滞后，政策变化可能影响市场
2. **流动性风险**: 部分期货品种流动性不足，可能影响执行
3. **模型风险**: 评分基于历史数据，未来表现可能偏离
4. **操作风险**: 期货交易杠杆高，严格控制仓位和止损

## 📊 数据源说明

- **Wind MCP**: 宏观经济数据、实体经济指标、期货行情（优先）
- **免费数据源**: akshare、新浪财经（Wind 不可用时回退）
- **GLM5**: AI 深度分析报告生成

---

*本报告由 GLM5 期货分析报告生成器自动生成*
*生成时间: {now}*
"""

    return md


def _get_macro_name(key: str) -> str:
    """获取宏观指标中文名"""
    names = {
        'pmi': '制造业PMI',
        'gdp': 'GDP同比',
        'cpi': 'CPI同比',
        'ppi': 'PPI同比',
        'm2': 'M2同比',
        '社融': '社融存量同比',
        '进出口': '进出口同比',
        '失业率': '城镇调查失业率',
    }
    return names.get(key, key)


def _get_macro_signal(key: str, value: float) -> str:
    """获取宏观指标信号"""
    if key == 'pmi':
        return "扩张🟢" if value >= 50 else "收缩🔴"
    elif key == 'cpi':
        if value >= 3: return "通胀🔴"
        elif value >= 0: return "温和🟢"
        else: return "通缩🔴"
    elif key == 'ppi':
        return "涨价🟢" if value > 0 else "降价🔴"
    elif key == 'm2':
        return "宽松🟢" if value >= 10 else "中性⚪"
    elif key == 'gdp':
        return "强劲🟢" if value >= 5.5 else ("稳健⚪" if value >= 4 else "疲弱🔴")
    else:
        return "中性⚪"


def main():
    parser = argparse.ArgumentParser(description="GLM5 期货分析报告生成器")
    parser.add_argument('--no-wind', action='store_true', help='不使用 Wind MCP')
    parser.add_argument('--no-glm5', action='store_true', help='不使用 GLM5')
    args = parser.parse_args()

    try:
        report_file = generate_report(
            use_wind=not args.no_wind,
            use_glm5=not args.no_glm5
        )
        print(f"\n✅ 报告生成完成: {report_file}")
    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
