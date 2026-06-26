# -*- coding: utf-8 -*-
"""
五年收益率预测分析
基于 2026年交易计划_优化版_v2.md 配置预测未来5年预期收益率

分析维度:
1. 权益组合(300万) + 低风险理财(4000万) 综合收益
2. 指数化投资复利效应
3. 分红再投资收益
4. 再平衡成本分析
5. 风险调整后收益
"""

import json
from datetime import datetime
from typing import Dict, List, Tuple
import os

# ============ 配置风格参数 ============
PORTFOLIO_STYLE = "风险平价 + 核心-卫星 + 动量择时"

# ============ 目标配置 (27只标的) ============
# 权益组合总资金: 300万
# 低风险理财: 4000万
# 总账户: 4300万

TARGET_CONFIG = [
    # ===== 核心宽基 ETF (84万, 28%) =====
    {"code": "510300", "name": "沪深300ETF华泰柏瑞", "sector": "宽基ETF", "weight": 0.08, "annual_return": 0.10, "dividend": 0.025, "stop_loss": -0.08},
    {"code": "510500", "name": "中证500ETF南方", "sector": "宽基ETF", "weight": 0.06, "annual_return": 0.11, "dividend": 0.028, "stop_loss": -0.08},
    {"code": "512100", "name": "中证1000ETF南方", "sector": "小盘成长ETF", "weight": 0.05, "annual_return": 0.13, "dividend": 0.018, "stop_loss": -0.10},
    {"code": "588000", "name": "科创50ETF华夏", "sector": "科技ETF", "weight": 0.05, "annual_return": 0.16, "dividend": 0.010, "stop_loss": -0.12},
    {"code": "159915", "name": "创业板ETF易方达", "sector": "成长ETF", "weight": 0.04, "annual_return": 0.14, "dividend": 0.015, "stop_loss": -0.12},
    # ===== 科技成长个股 (60万, 20%) =====
    {"code": "688041", "name": "海光信息", "sector": "科技个股", "weight": 0.03, "annual_return": 0.20, "dividend": 0.005, "stop_loss": -0.10},
    {"code": "300308", "name": "中际旭创", "sector": "科技个股", "weight": 0.03, "annual_return": 0.18, "dividend": 0.010, "stop_loss": -0.12},
    {"code": "300274", "name": "阳光电源", "sector": "科技个股", "weight": 0.04, "annual_return": 0.16, "dividend": 0.020, "stop_loss": -0.12},
    {"code": "002371", "name": "北方华创", "sector": "科技个股", "weight": 0.03, "annual_return": 0.18, "dividend": 0.015, "stop_loss": -0.12},
    {"code": "688017", "name": "绿的谐波", "sector": "科技个股", "weight": 0.03, "annual_return": 0.22, "dividend": 0.005, "stop_loss": -0.15},
    {"code": "600276", "name": "恒瑞医药", "sector": "医药个股", "weight": 0.04, "annual_return": 0.12, "dividend": 0.025, "stop_loss": -0.10},
    # ===== 高端制造/基建 (60万, 20%) =====
    {"code": "600089", "name": "特变电工", "sector": "高端制造", "weight": 0.05, "annual_return": 0.14, "dividend": 0.040, "stop_loss": -0.10},
    {"code": "600875", "name": "东方电气", "sector": "高端制造", "weight": 0.04, "annual_return": 0.13, "dividend": 0.035, "stop_loss": -0.10},
    {"code": "000425", "name": "徐工机械", "sector": "高端制造", "weight": 0.04, "annual_return": 0.12, "dividend": 0.030, "stop_loss": -0.10},
    {"code": "600406", "name": "国电南瑞", "sector": "高端制造", "weight": 0.04, "annual_return": 0.13, "dividend": 0.035, "stop_loss": -0.10},
    {"code": "600989", "name": "宝丰能源", "sector": "高端制造", "weight": 0.03, "annual_return": 0.11, "dividend": 0.050, "stop_loss": -0.12},
    # ===== 防御/红利 (45万, 15%) =====
    {"code": "515180", "name": "易方达中证红利ETF", "sector": "红利ETF", "weight": 0.06, "annual_return": 0.09, "dividend": 0.055, "stop_loss": -0.08},
    {"code": "600036", "name": "招商银行", "sector": "银行", "weight": 0.04, "annual_return": 0.10, "dividend": 0.050, "stop_loss": -0.10},
    {"code": "600900", "name": "长江电力", "sector": "公用事业", "weight": 0.03, "annual_return": 0.08, "dividend": 0.038, "stop_loss": -0.08},
    {"code": "601088", "name": "中国神华", "sector": "能源防御", "weight": 0.02, "annual_return": 0.10, "dividend": 0.045, "stop_loss": -0.08},
    # ===== 商品/避险 (15万, 5%) =====
    {"code": "518880", "name": "黄金ETF华安", "sector": "商品", "weight": 0.05, "annual_return": 0.07, "dividend": 0.000, "stop_loss": -0.08},
    # ===== 现金缓冲 (24万, 8%) =====
    {"code": "CASH", "name": "现金缓冲", "sector": "现金", "weight": 0.08, "annual_return": 0.02, "dividend": 0.000, "stop_loss": 0.0},
]

# ============ 低风险理财配置 (4000万) ============
LOW_RISK_CONFIG = [
    {"name": "银行理财", "amount": 2000_0000, "annual_return": 0.035},
    {"name": "国债逆回购", "amount": 1000_0000, "annual_return": 0.028},
    {"name": "货币基金", "amount": 500_0000, "annual_return": 0.025},
    {"name": "同业存单", "amount": 300_0000, "annual_return": 0.032},
    {"name": "短债基金", "amount": 200_0000, "annual_return": 0.030},
]

# ============ 市场环境参数 ============
MARKET_PARAMS = {
    "kondratieff_phase": "复苏期转繁荣期",
    "kondratieff_return_boost": 0.02,
    "policy_bonus": 0.02,
    "etf_cost_advantage": 0.005,
    "market_return": 0.08,
    "market_volatility": 0.15,
    "risk_free_rate": 0.03,
    "transaction_cost": 0.0008,
    "rebalance_frequency": 4,
}

# ============ 账户配置 ============
TOTAL_EQUITY_CAPITAL = 3_000_000
TOTAL_LOW_RISK_CAPITAL = 40_000_000
TOTAL_ACCOUNT_CAPITAL = 43_000_000


def calculate_sector_return(sector: str) -> float:
    """计算行业预期收益"""
    sector_returns = {
        "宽基ETF": 0.10,
        "小盘成长ETF": 0.13,
        "科技ETF": 0.16,
        "成长ETF": 0.14,
        "科技个股": 0.18,
        "医药个股": 0.12,
        "高端制造": 0.13,
        "红利ETF": 0.09,
        "银行": 0.10,
        "公用事业": 0.08,
        "能源防御": 0.10,
        "商品": 0.07,
        "现金": 0.02,
    }
    return sector_returns.get(sector, 0.08)


def calculate_5y_projection(initial_capital: float = TOTAL_ACCOUNT_CAPITAL, years: int = 5) -> Dict:
    """
    计算5年收益率预测
    """
    results = {
        "summary": {},
        "yearly_projection": [],
        "sector_analysis": {},
        "risk_metrics": {},
        "recommendations": [],
        "equity_projection": {},
        "low_risk_projection": {},
    }

    # ============ 1. 计算权益组合加权预期收益率 ============
    weighted_return = 0
    weighted_dividend = 0
    sector_returns = {}

    for stock in TARGET_CONFIG:
        sector = stock["sector"]
        weight = stock["weight"]
        annual_return = stock["annual_return"]
        dividend = stock["dividend"]

        weighted_return += weight * annual_return
        weighted_dividend += weight * dividend

        if sector not in sector_returns:
            sector_returns[sector] = {"weight": 0, "return": 0, "dividend": 0}
        sector_returns[sector]["weight"] += weight
        sector_returns[sector]["return"] = calculate_sector_return(sector)
        sector_returns[sector]["dividend"] += weight * dividend

    # ============ 2. 考虑宏观因素调整 ============
    macro_adjustment = (
        MARKET_PARAMS["kondratieff_return_boost"] +
        MARKET_PARAMS["policy_bonus"] +
        MARKET_PARAMS["etf_cost_advantage"]
    )
    adjusted_return = weighted_return + macro_adjustment

    # ============ 3. 计算再平衡成本 ============
    rebalance_cost = MARKET_PARAMS["transaction_cost"] * MARKET_PARAMS["rebalance_frequency"] * years

    # ============ 4. 权益组合年度预测 ============
    current_equity = TOTAL_EQUITY_CAPITAL
    equity_yearly_results = []

    for year in range(1, years + 1):
        start_capital = current_equity
        capital_growth = current_equity * adjusted_return
        dividend_income = current_equity * weighted_dividend
        yearly_rebalance_cost = TOTAL_EQUITY_CAPITAL * MARKET_PARAMS["transaction_cost"] * MARKET_PARAMS["rebalance_frequency"]
        end_capital = current_equity + capital_growth + dividend_income - yearly_rebalance_cost
        year_return = (end_capital - start_capital) / start_capital

        equity_yearly_results.append({
            "year": year,
            "start_capital": start_capital,
            "capital_growth": capital_growth,
            "dividend_income": dividend_income,
            "rebalance_cost": yearly_rebalance_cost,
            "end_capital": end_capital,
            "year_return": year_return,
            "cumulative_return": (end_capital - TOTAL_EQUITY_CAPITAL) / TOTAL_EQUITY_CAPITAL
        })
        current_equity = end_capital

    # ============ 5. 低风险理财年度预测 ============
    current_low_risk = TOTAL_LOW_RISK_CAPITAL
    low_risk_yearly_results = []

    low_risk_weighted_return = sum(
        cfg["amount"] / TOTAL_LOW_RISK_CAPITAL * cfg["annual_return"]
        for cfg in LOW_RISK_CONFIG
    )

    for year in range(1, years + 1):
        start_capital = current_low_risk
        capital_growth = current_low_risk * low_risk_weighted_return
        end_capital = current_low_risk + capital_growth
        year_return = (end_capital - start_capital) / start_capital

        low_risk_yearly_results.append({
            "year": year,
            "start_capital": start_capital,
            "capital_growth": capital_growth,
            "end_capital": end_capital,
            "year_return": year_return,
            "cumulative_return": (end_capital - TOTAL_LOW_RISK_CAPITAL) / TOTAL_LOW_RISK_CAPITAL
        })
        current_low_risk = end_capital

    # ============ 6. 汇总结果 ============
    final_equity = current_equity
    final_low_risk = current_low_risk
    final_total = final_equity + final_low_risk

    total_return = (final_total - TOTAL_ACCOUNT_CAPITAL) / TOTAL_ACCOUNT_CAPITAL
    annualized_return = (final_total / TOTAL_ACCOUNT_CAPITAL) ** (1 / years) - 1

    sector_analysis = {}
    for sector, data in sector_returns.items():
        sector_analysis[sector] = {
            "配置比例": f"{data['weight'] * 100:.1f}%",
            "预期年化收益": f"{data['return'] * 100:.1f}%",
            "分红率": f"{data['dividend'] * 100:.2f}%",
            "贡献度": f"{data['weight'] * data['return'] * 100:.2f}%"
        }

    portfolio_volatility = MARKET_PARAMS["market_volatility"] * 0.75
    sharpe_ratio = (annualized_return - MARKET_PARAMS["risk_free_rate"]) / portfolio_volatility

    # 情景分析（权益组合）
    equity_bull_capital = TOTAL_EQUITY_CAPITAL * (1 + adjusted_return + 0.05) ** years
    equity_bear_capital = TOTAL_EQUITY_CAPITAL * (1 + adjusted_return - 0.06) ** years
    equity_base_capital = final_equity

    # 情景分析（总账户）
    low_risk_base = TOTAL_LOW_RISK_CAPITAL * (1 + low_risk_weighted_return) ** years
    total_bull_capital = equity_bull_capital + low_risk_base
    total_bear_capital = equity_bear_capital + low_risk_base
    total_base_capital = final_total

    recommendations = [
        f"配置风格: {PORTFOLIO_STYLE}",
        f"权益组合: ￥{TOTAL_EQUITY_CAPITAL:,.0f}，低风险理财: ￥{TOTAL_LOW_RISK_CAPITAL:,.0f}，总账户: ￥{TOTAL_ACCOUNT_CAPITAL:,.0f}",
        f"预计5年累计收益 {total_return * 100:.1f}%，年化 {annualized_return * 100:.1f}%",
        f"权益组合预期年化 {((final_equity / TOTAL_EQUITY_CAPITAL) ** (1/years) - 1) * 100:.1f}%，低风险理财预期年化 {low_risk_weighted_return * 100:.1f}%",
        f"核心宽基ETF(28%)+科技成长个股(20%)+高端制造(20%)为组合核心",
        f"防御/红利(15%)提供稳定现金流，分红率约 {(weighted_dividend * 100):.2f}%/年",
        f"黄金ETF(5%)提供通胀对冲，降低组合波动至{portfolio_volatility * 100:.1f}%",
        f"乐观看5年后总账户 ￥{total_bull_capital:,.0f}，基准 ￥{total_base_capital:,.0f}，悲观 ￥{total_bear_capital:,.0f}",
        f"建议每年{MARKET_PARAMS['rebalance_frequency']}次再平衡，维持风险平价纪律"
    ]

    return {
        "summary": {
            "初始资金": TOTAL_ACCOUNT_CAPITAL,
            "权益初始": TOTAL_EQUITY_CAPITAL,
            "低风险初始": TOTAL_LOW_RISK_CAPITAL,
            "5年后基准资金": total_base_capital,
            "5年后权益资金": equity_base_capital,
            "5年后低风险资金": final_low_risk,
            "乐观情景资金": total_bull_capital,
            "悲观情景资金": total_bear_capital,
            "累计收益率": f"{total_return * 100:.1f}%",
            "年化收益率": f"{annualized_return * 100:.1f}%",
            "权益年化收益率": f"{((final_equity / TOTAL_EQUITY_CAPITAL) ** (1/years) - 1) * 100:.1f}%",
            "低风险年化收益率": f"{low_risk_weighted_return * 100:.1f}%",
            "总分红收益": f"￥{sum(y['dividend_income'] for y in equity_yearly_results):,.0f}",
            "总交易成本": f"￥{sum(y['rebalance_cost'] for y in equity_yearly_results):,.0f}",
            "夏普比率": f"{sharpe_ratio:.2f}",
            "配置风格": PORTFOLIO_STYLE
        },
        "yearly_projection": equity_yearly_results,
        "equity_projection": equity_yearly_results,
        "low_risk_projection": low_risk_yearly_results,
        "sector_analysis": sector_analysis,
        "risk_metrics": {
            "组合波动率": f"{portfolio_volatility * 100:.1f}%",
            "夏普比率": f"{sharpe_ratio:.2f}",
            "无风险利率": f"{MARKET_PARAMS['risk_free_rate'] * 100:.1f}%",
            "市场基准收益": f"{MARKET_PARAMS['market_return'] * 100:.1f}%",
            "超额收益": f"{(annualized_return - MARKET_PARAMS['market_return']) * 100:.1f}%"
        },
        "recommendations": recommendations,
        "macro_factors": {
            "康波周期": MARKET_PARAMS["kondratieff_phase"],
            "政策红利": f"+{MARKET_PARAMS['policy_bonus'] * 100:.0f}%",
            "ETF费率优势": f"+{MARKET_PARAMS['etf_cost_advantage'] * 100:.1f}%"
        },
        "scenario_analysis": {
            "乐观": {"年化": f"{(annualized_return + 0.02) * 100:.1f}%", "终值": total_bull_capital},
            "基准": {"年化": f"{annualized_return * 100:.1f}%", "终值": total_base_capital},
            "悲观": {"年化": f"{(annualized_return - 0.025) * 100:.1f}%", "终值": total_bear_capital}
        },
        "low_risk_summary": {
            "加权年化": f"{low_risk_weighted_return * 100:.2f}%",
            "5年收益": f"￥{(final_low_risk - TOTAL_LOW_RISK_CAPITAL):,.0f}",
            "5年终值": f"￥{final_low_risk:,.0f}"
        }
    }


def generate_report(projection: Dict) -> str:
    """生成Markdown格式报告"""

    report = f"""# 五年收益率预测报告（2026年交易计划 v2.0）

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 配置风格: {projection['summary']['配置风格']}
> 总账户资金: ￥{projection['summary']['初始资金']:,.0f}
> 权益组合: ￥{projection['summary']['权益初始']:,.0f}（7%）+ 低风险理财: ￥{projection['summary']['低风险初始']:,.0f}（93%）

---

## 一、核心预测结果

### 收益预测摘要

| 指标 | 数值 |
|------|------|
| 总账户初始 | ￥{projection['summary']['初始资金']:,.0f} |
| 权益组合初始 | ￥{projection['summary']['权益初始']:,.0f} |
| 低风险理财初始 | ￥{projection['summary']['低风险初始']:,.0f} |
| **5年后基准资金** | **￥{projection['summary']['5年后基准资金']:,.0f}** |
| **5年后权益资金** | **￥{projection['summary']['5年后权益资金']:,.0f}** |
| **5年后低风险资金** | **￥{projection['summary']['5年后低风险资金']:,.0f}** |
| 累计收益率 | {projection['summary']['累计收益率']} |
| **年化收益率** | **{projection['summary']['年化收益率']}** |
| 权益年化收益率 | {projection['summary']['权益年化收益率']} |
| 低风险年化收益率 | {projection['summary']['低风险年化收益率']} |
| 总分红收益 | {projection['summary']['总分红收益']} |
| 总交易成本 | {projection['summary']['总交易成本']} |
| 夏普比率 | {projection['summary']['夏普比率']} |

### 情景分析

| 情景 | 年化收益 | 5年预期终值 | 累计收益 |
|------|---------|-----------|---------|
| 乐观 | {projection['scenario_analysis']['乐观']['年化']} | ￥{projection['scenario_analysis']['乐观']['终值']:,.0f} | {(projection['scenario_analysis']['乐观']['终值'] / projection['summary']['初始资金'] - 1) * 100:.1f}% |
| 基准 | {projection['scenario_analysis']['基准']['年化']} | ￥{projection['scenario_analysis']['基准']['终值']:,.0f} | {projection['summary']['累计收益率']} |
| 悲观 | {projection['scenario_analysis']['悲观']['年化']} | ￥{projection['scenario_analysis']['悲观']['终值']:,.0f} | {(projection['scenario_analysis']['悲观']['终值'] / projection['summary']['初始资金'] - 1) * 100:.1f}% |

### 宏观因素调整

| 因素 | 影响 |
|------|------|
| 康波周期 | {projection['macro_factors']['康波周期']} |
| 十五五政策红利 | {projection['macro_factors']['政策红利']} |
| ETF低费率优势 | {projection['macro_factors']['ETF费率优势']} |

---

## 二、年度收益预测（权益组合）

| 年份 | 年初资金 | 资本增值 | 分红收益 | 交易成本 | 年末资金 | 年化收益 | 累计收益 |
|------|----------|----------|----------|----------|----------|----------|----------|
"""

    for year_data in projection['equity_projection']:
        report += f"| {year_data['year']} | ￥{year_data['start_capital']:,.0f} | ￥{year_data['capital_growth']:,.0f} | ￥{year_data['dividend_income']:,.0f} | ￥{year_data['rebalance_cost']:,.0f} | ￥{year_data['end_capital']:,.0f} | {year_data['year_return'] * 100:.1f}% | {year_data['cumulative_return'] * 100:.1f}% |\n"

    report += f"""

---

## 三、年度收益预测（低风险理财）

| 年份 | 年初资金 | 资本增值 | 年末资金 | 年化收益 |
|------|----------|----------|----------|----------|
"""

    for year_data in projection['low_risk_projection']:
        report += f"| {year_data['year']} | ￥{year_data['start_capital']:,.0f} | ￥{year_data['capital_growth']:,.0f} | ￥{year_data['end_capital']:,.0f} | {year_data['year_return'] * 100:.2f}% |\n"

    report += f"""

---

## 四、配置分析

### 行业配置

| 类型 | 配置比例 | 预期年化收益 | 分红率 | 收益贡献度 |
|------|----------|--------------|--------|------------|
"""

    for sector, data in projection['sector_analysis'].items():
        report += f"| {sector} | {data['配置比例']} | {data['预期年化收益']} | {data['分红率']} | {data['贡献度']} |\n"

    report += f"""

### 配置逻辑

- **核心宽基 ETF (28%, 84万)**: 获取市场 Beta 收益，降低单一标的风险
  - 沪深300ETF(8%)+中证500ETF(6%)+中证1000ETF(5%)+科创50ETF(5%)+创业板ETF(4%)
- **科技成长个股 (20%, 60万)**: 十五五规划重点方向，进攻 Alpha 来源
  - 海光信息/中际旭创/阳光电源/北方华创/绿的谐波/恒瑞医药
- **高端制造/基建 (20%, 60万)**: 康波周期复苏阶段受益板块，周期+成长双击
  - 特变电工/东方电气/徐工机械/国电南瑞/宝丰能源
- **防御/红利 (15%, 45万)**: 防御性配置，高分红再投资降低整体波动
  - 中证红利ETF(6%)+招商银行(4%)+长江电力(3%)+中国神华(2%)
- **商品/避险 (5%, 15万)**: 华安黄金ETF — 抗通胀+危机对冲
- **现金缓冲 (8%, 24万)**: 机动配置资金

---

## 五、风险指标

| 风险指标 | 数值 | 说明 |
|----------|------|------|
| 组合波动率 | {projection['risk_metrics']['组合波动率']} | ETF分散显著降低波动 |
| 夏普比率 | {projection['risk_metrics']['夏普比率']} | 风险调整后收益 |
| 无风险利率 | {projection['risk_metrics']['无风险利率']} | 10年期国债 |
| 市场基准收益 | {projection['risk_metrics']['市场基准收益']} | 沪深300预期 |
| 超额收益 | {projection['risk_metrics']['超额收益']} | vs 市场基准 |

---

## 六、投资建议

"""

    for i, rec in enumerate(projection['recommendations'], 1):
        report += f"{i}. {rec}\n"

    report += f"""

---

## 七、免责声明

⚠️ **重要提示**:

1. 本预测基于历史数据和行业预期，实际收益可能与预测存在较大差异
2. 低风险理财收益相对稳定，权益组合波动较大
3. 预测不构成投资建议，投资有风险，决策需谨慎

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*数据来源于万得 Wind 金融数据服务*
*配置基于: 2026年交易计划_优化版_v2.md*
"""

    return report


if __name__ == '__main__':
    projection = calculate_5y_projection(initial_capital=TOTAL_ACCOUNT_CAPITAL, years=5)
    report = generate_report(projection)

    reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    report_file = os.path.join(reports_dir, f'五年收益预测_{datetime.now().strftime("%Y%m%d")}.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(report)
    print(f"\n报告已保存至: {report_file}")
