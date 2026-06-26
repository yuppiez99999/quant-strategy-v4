# -*- coding: utf-8 -*-
"""
2026年底前完整交易计划
时间范围: 2026-06-12 至 2026-12-31

核心策略:
1. 基于十五五规划+康波周期配置
2. 重点布局高端制造、科技创新、能源转型
3. 动态再平衡，控制回撤风险
"""

import os
import json
from datetime import datetime, timedelta

# 计划参数
START_DATE = datetime(2026, 6, 12)
END_DATE = datetime(2026, 12, 31)
TOTAL_CAPITAL = 529590.0  # 当前账户总值

# 目标资产配置(基于十五五规划+康波周期)
TARGET_ALLOCATION = {
    "equity": {
        "tech_growth": {
            "weight": 0.45,  # 45% 科技成长
            "sub_sectors": [
                {"name": "科创50ETF", "code": "588000", "weight": 0.20},
                {"name": "创业板ETF", "code": "159915", "weight": 0.15},
                {"name": "半导体ETF", "code": "512760", "weight": 0.10},
            ]
        },
        "broad_market": {
            "weight": 0.25,  # 25% 宽基指数
            "sub_sectors": [
                {"name": "沪深300ETF", "code": "510300", "weight": 0.15},
                {"name": "中证1000ETF", "code": "512100", "weight": 0.10},
            ]
        },
        "thematic": {
            "weight": 0.15,  # 15% 主题投资
            "sub_sectors": [
                {"name": "新能源车ETF", "code": "515030", "weight": 0.08},
                {"name": "医药ETF", "code": "512170", "weight": 0.07},
            ]
        },
        "total": 0.85  # 权益类总计85%
    },
    "alternative": {
        "commodity": {
            "weight": 0.10,  # 10% 商品/黄金
            "sub_sectors": [
                {"name": "华安黄金ETF", "code": "518880", "weight": 0.10},
            ]
        },
        "cash": {
            "weight": 0.05,  # 5% 现金
        },
        "total": 0.15  # 另类投资总计15%
    }
}

# 关键时间节点
KEY_MILESTONES = [
    {"date": "2026-06-15", "event": "Q2季度再平衡", "action": "执行首次调仓"},
    {"date": "2026-06-30", "event": "Q2财报季", "action": "关注业绩披露"},
    {"date": "2026-07-01", "event": "下半年投资策略调整", "action": "基于半年报调整持仓"},
    {"date": "2026-08-15", "event": "中期再平衡", "action": "评估上半年表现"},
    {"date": "2026-09-30", "event": "Q3财报季", "action": "关注业绩变化"},
    {"date": "2026-10-01", "event": "四季度布局", "action": "跨年行情准备"},
    {"date": "2026-11-15", "event": "年度再平衡", "action": "调整至年终目标配置"},
    {"date": "2026-12-15", "event": "年终盘点", "action": "业绩总结与税务规划"},
    {"date": "2026-12-31", "event": "年度结算", "action": "年度收益结算"},
]

# 风险控制参数
RISK_PARAMS = {
    "max_drawdown": 0.15,  # 最大回撤15%
    "single_stock_limit": 0.10,  # 单只股票上限10%
    "sector_limit": 0.30,  # 单一行业上限30%
    "rebalance_threshold": 0.05,  # 再平衡阈值5%
    "stop_loss": 0.08,  # 止损8%
    "take_profit": 0.20,  # 止盈20%
}

def generate_trading_plan():
    """生成完整交易计划"""
    plan = {
        "title": "2026年底前完整交易计划",
        "start_date": START_DATE.strftime("%Y-%m-%d"),
        "end_date": END_DATE.strftime("%Y-%m-%d"),
        "duration_days": (END_DATE - START_DATE).days,
        "total_capital": TOTAL_CAPITAL,
        "investment_goals": [],
        "asset_allocation": {},
        "milestones": [],
        "risk_management": {},
        "monthly_plan": [],
        "execution_summary": {}
    }
    
    # 投资目标
    plan["investment_goals"] = [
        {
            "goal": "年度收益目标",
            "target": "15-20%",
            "basis": "基于康波周期复苏阶段预期",
        },
        {
            "goal": "最大回撤控制",
            "target": "<=15%",
            "basis": "通过分散配置和止损机制",
        },
        {
            "goal": "跑赢大盘",
            "target": "超越沪深300指数5个百分点",
            "basis": "主动配置alpha策略",
        },
        {
            "goal": "资产增值",
            "target": "账户总值突破65万元",
            "basis": "实现15%收益目标",
        },
    ]
    
    # 资产配置
    plan["asset_allocation"] = TARGET_ALLOCATION
    
    # 关键时间节点
    plan["milestones"] = KEY_MILESTONES
    
    # 风险管理
    plan["risk_management"] = RISK_PARAMS
    
    # 月度计划
    months = []
    current_month = START_DATE.month
    while current_month <= END_DATE.month:
        month_start = datetime(2026, current_month, 1)
        month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        
        if current_month == 6:
            theme = "上半年收官与策略调整"
            focus = "执行Q2再平衡，布局下半年"
        elif current_month == 7:
            theme = "中期策略布局"
            focus = "基于半年报调整持仓结构"
        elif current_month == 8:
            theme = "中报行情"
            focus = "关注中报业绩，动态调仓"
        elif current_month == 9:
            theme = "三季度冲刺"
            focus = "Q3财报季，优化组合"
        elif current_month == 10:
            theme = "四季度开局"
            focus = "跨年行情布局，科技主线"
        elif current_month == 11:
            theme = "年终冲刺"
            focus = "年度再平衡，锁定收益"
        elif current_month == 12:
            theme = "年度收官"
            focus = "业绩结算，税务规划"
        
        months.append({
            "month": current_month,
            "period": f"{month_start.strftime('%Y-%m-%d')} ~ {month_end.strftime('%Y-%m-%d')}",
            "theme": theme,
            "focus": focus,
            "target_pct": round((current_month - 5) * 3, 1),  # 累计目标进度
        })
        
        current_month += 1
    
    plan["monthly_plan"] = months
    
    # 执行摘要
    plan["execution_summary"] = {
        "total_trades_expected": 20-30,
        "rebalance_frequency": "每月一次",
        "review_frequency": "每周复盘",
        "report_frequency": "每日收盘报告",
    }
    
    return plan

def generate_md_report(plan):
    """生成Markdown格式报告"""
    lines = []
    lines.append("# 2026年底前完整交易计划")
    lines.append("")
    lines.append(f"> 执行周期: {plan['start_date']} ~ {plan['end_date']}")
    lines.append(f"> 计划时长: {plan['duration_days']} 天")
    lines.append(f"> 初始资金: ¥ {plan['total_capital']:,.2f}")
    lines.append("")
    
    # 投资目标
    lines.append("## 一、投资目标")
    lines.append("")
    for goal in plan["investment_goals"]:
        lines.append(f"### 🎯 {goal['goal']}")
        lines.append(f"- **目标**: {goal['target']}")
        lines.append(f"- **依据**: {goal['basis']}")
        lines.append("")
    
    # 资产配置
    lines.append("## 二、资产配置方案")
    lines.append("")
    lines.append("### 2.1 大类资产配置")
    lines.append("")
    lines.append("| 资产类别 | 权重 | 说明 |")
    lines.append("|:---------|-----:|:-----|")
    lines.append(f"| 权益类 | {plan['asset_allocation']['equity']['total']*100:.0f}% | 科技成长+宽基+主题 |")
    lines.append(f"| 商品/黄金 | {plan['asset_allocation']['alternative']['commodity']['weight']*100:.0f}% | 避险对冲 |")
    lines.append(f"| 现金 | {plan['asset_allocation']['alternative']['cash']['weight']*100:.0f}% | 流动性储备 |")
    lines.append("")
    
    lines.append("### 2.2 权益类细分配置")
    lines.append("")
    lines.append("| 板块 | 权重 | 标的 |")
    lines.append("|:-----|-----:|:-----|")
    
    # 科技成长
    for sub in plan["asset_allocation"]["equity"]["tech_growth"]["sub_sectors"]:
        lines.append(f"| 科技成长 | {sub['weight']*100:.0f}% | {sub['name']} ({sub['code']}) |")
    
    # 宽基指数
    for sub in plan["asset_allocation"]["equity"]["broad_market"]["sub_sectors"]:
        lines.append(f"| 宽基指数 | {sub['weight']*100:.0f}% | {sub['name']} ({sub['code']}) |")
    
    # 主题投资
    for sub in plan["asset_allocation"]["equity"]["thematic"]["sub_sectors"]:
        lines.append(f"| 主题投资 | {sub['weight']*100:.0f}% | {sub['name']} ({sub['code']}) |")
    
    # 商品
    for sub in plan["asset_allocation"]["alternative"]["commodity"]["sub_sectors"]:
        lines.append(f"| 商品黄金 | {sub['weight']*100:.0f}% | {sub['name']} ({sub['code']}) |")
    
    lines.append("")
    
    # 关键时间节点
    lines.append("## 三、关键时间节点")
    lines.append("")
    lines.append("| 日期 | 事件 | 行动 |")
    lines.append("|:-----|:-----|:-----|")
    for milestone in plan["milestones"]:
        lines.append(f"| {milestone['date']} | {milestone['event']} | {milestone['action']} |")
    lines.append("")
    
    # 月度计划
    lines.append("## 四、月度行动计划")
    lines.append("")
    for month in plan["monthly_plan"]:
        lines.append(f"### 📅 {month['period']}")
        lines.append(f"**主题**: {month['theme']}")
        lines.append(f"**重点**: {month['focus']}")
        lines.append("")
    
    # 风险管理
    lines.append("## 五、风险控制策略")
    lines.append("")
    rp = plan["risk_management"]
    lines.append("| 风控指标 | 阈值 | 说明 |")
    lines.append("|:---------|:-----|:-----|")
    lines.append(f"| 最大回撤 | {rp['max_drawdown']*100:.0f}% | 触发后减仓至中性仓位 |")
    lines.append(f"| 单只股票上限 | {rp['single_stock_limit']*100:.0f}% | 防止过度集中 |")
    lines.append(f"| 单一行业上限 | {rp['sector_limit']*100:.0f}% | 分散行业风险 |")
    lines.append(f"| 再平衡阈值 | {rp['rebalance_threshold']*100:.0f}% | 权重偏差超过时调仓 |")
    lines.append(f"| 止损 | {rp['stop_loss']*100:.0f}% | 单标的止损线 |")
    lines.append(f"| 止盈 | {rp['take_profit']*100:.0f}% | 单标的止盈线 |")
    lines.append("")
    
    # 执行机制
    lines.append("## 六、执行机制")
    lines.append("")
    es = plan["execution_summary"]
    lines.append(f"- **预期交易次数**: {es['total_trades_expected']}笔")
    lines.append(f"- **再平衡频率**: {es['rebalance_frequency']}")
    lines.append(f"- **复盘频率**: {es['review_frequency']}")
    lines.append(f"- **报告频率**: {es['report_frequency']}")
    lines.append("")
    
    # 总结
    lines.append("---")
    lines.append("")
    lines.append("## 七、策略核心要点")
    lines.append("")
    lines.append("1. **战略方向**: 聚焦十五五规划重点领域，布局高端制造、科技创新")
    lines.append("2. **战术执行**: 每月再平衡，动态调整权重")
    lines.append("3. **风险控制**: 严格执行止损止盈，控制最大回撤")
    lines.append("4. **业绩追踪**: 每日报告、每周复盘、每月评估")
    lines.append("")
    lines.append("**风险提示**: 投资有风险，本计划仅供参考，实际操作需根据市场情况调整。")
    lines.append("")
    
    return "\n".join(lines)

def save_plan(plan, filepath):
    """保存计划到JSON文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"计划已保存: {filepath}")

def save_md_report(content, filepath):
    """保存Markdown报告"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"报告已保存: {filepath}")

if __name__ == "__main__":
    # 生成计划
    plan = generate_trading_plan()
    
    # 打印摘要
    print("="*60)
    print(" 2026年底前完整交易计划")
    print("="*60)
    print(f" 执行周期: {plan['start_date']} ~ {plan['end_date']}")
    print(f" 计划时长: {plan['duration_days']} 天")
    print(f" 初始资金: {plan['total_capital']:,.2f}")
    print("="*60)
    
    print("\n【投资目标】")
    for goal in plan["investment_goals"]:
        print(f"    {goal['goal']}: {goal['target']}")
    
    print("\n【资产配置】")
    print(f"    权益类: {plan['asset_allocation']['equity']['total']*100:.0f}%")
    print(f"    商品黄金: {plan['asset_allocation']['alternative']['commodity']['weight']*100:.0f}%")
    print(f"    现金: {plan['asset_allocation']['alternative']['cash']['weight']*100:.0f}%")
    
    print("\n【关键时间节点】")
    for milestone in plan["milestones"][:5]:
        print(f"    {milestone['date']}: {milestone['event']}")
    
    # 保存文件
    output_dir = r"E:\各种PY程序\每日报告归档\交易计划"
    os.makedirs(output_dir, exist_ok=True)
    
    json_path = os.path.join(output_dir, "2026年底交易计划.json")
    save_plan(plan, json_path)
    
    md_content = generate_md_report(plan)
    md_path = os.path.join(output_dir, "2026年底交易计划.md")
    save_md_report(md_content, md_path)
    
    print(f"\n交易计划已生成，文件保存在: {output_dir}")