#!/usr/bin/env python3
"""
职业投资训练模型 - 一键运行版
直接执行完整分析，无需交互
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from career_investor_lite import CareerInvestorLite


def generate_markdown_report(results, output_path):
    """生成Markdown格式报告"""
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    portfolio = results.get('portfolio', {})
    risk = results.get('risk', {})
    signals = results.get('signals', [])
    backtest = results.get('backtest', {})
    prediction = results.get('prediction', {})
    
    md = f"""# 职业投资训练模型 - 分析报告

> 生成时间: {now}
> 需求编号: 1770371634132965

---

## 一、持仓组合概况

| 指标 | 数值 |
|------|------|
| 持仓标的数 | {portfolio.get('total_assets', 0)} 只 |
| 股票总权重 | {portfolio.get('total_weight', 0)*100:.1f}% |
| 现金比例 | {portfolio.get('cash_ratio', 0)*100:.1f}% |

---

## 二、风险评估

| 指标 | 数值 |
|------|------|
| 风险等级 | {risk.get('risk_level', 'N/A')} |
| 组合VaR(95%) | {risk.get('var_95', 0):.2f}% |
| 最大回撤 | {risk.get('max_drawdown', 0):.2f}% |
| 波动率 | {risk.get('volatility', 0):.2f}% |

**建议**: {risk.get('recommendation', 'N/A')}

---

## 三、交易信号

| 代码 | 名称 | 信号 | 强度 | 原因 |
|------|------|------|------|------|
"""
    
    for sig in signals:
        md += f"| {sig.get('code', '')} | {sig.get('name', '')} | {sig.get('action', '')} | {sig.get('strength', 0):.2f} | {sig.get('reason', '')} |\n"
    
    buy_count = sum(1 for s in signals if s.get('action') == 'BUY')
    sell_count = sum(1 for s in signals if s.get('action') == 'SELL')
    hold_count = sum(1 for s in signals if s.get('action') == 'HOLD')
    
    md += f"""
**信号统计**: 买入 {buy_count} | 卖出 {sell_count} | 持有 {hold_count}

---

## 四、策略回测（2021-2026）

| 指标 | 数值 |
|------|------|
| 总收益率 | {backtest.get('total_return', 0):.2f}% |
| 年化收益率 | {backtest.get('annual_return', 0):.2f}% |
| 最大回撤 | {backtest.get('max_drawdown', 0):.2f}% |
| 夏普比率 | {backtest.get('sharpe_ratio', 0):.2f} |
| 交易次数 | {backtest.get('trade_count', 0)} |
| 胜率 | {backtest.get('win_rate', 0):.1f}% |

---

## 五、5年收益预测（蒙特卡洛模拟）

| 情景 | 预期市值 |
|------|----------|
| 初始资金 | {prediction.get('initial_capital', 2000000):,.0f} RMB |
| 预期均值 | {prediction.get('mean', 0):,.0f} RMB |
| 中位数 | {prediction.get('median', 0):,.0f} RMB |
| 悲观（5%） | {prediction.get('p5', 0):,.0f} RMB |
| 乐观（95%） | {prediction.get('p95', 0):,.0f} RMB |

**解读**:
- 有95%概率最终市值不低于 {prediction.get('p5', 0):,.0f} RMB
- 有5%概率最终市值超过 {prediction.get('p95', 0):,.0f} RMB
- 中位数 {prediction.get('median', 0):,.0f} 表示一半情况更好，一半更差

---

## 六、综合投资建议

"""
    
    recommendations = results.get('recommendations', [])
    for i, rec in enumerate(recommendations, 1):
        md += f"{i}. {rec}\n"
    
    md += f"""
---

*本报告由职业投资训练模型系统自动生成*
*数据来源：模拟数据（实际使用时对接Wind MCP/iFinD）*
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)
    
    return output_path


def main():
    """一键执行完整分析"""
    print("\n" + "="*70)
    print("  职业投资训练模型系统 - 一键分析报告")
    print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # 初始化模型
    model = CareerInvestorLite()
    
    # 执行完整分析
    results = model.full_analysis()
    
    # 保存JSON报告
    json_output = Path(__file__).parent / "investment_report.json"
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 生成Markdown报告
    md_output = Path(__file__).parent / "investment_report.md"
    generate_markdown_report(results, md_output)
    
    print(f"\n[报告已保存]")
    print(f"  JSON格式: {json_output}")
    print(f"  Markdown: {md_output}")
    print("\n" + "="*70)
    print("  分析完成！")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
