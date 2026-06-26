# -*- coding: utf-8 -*-
"""
每周一再平衡策略执行脚本
基于收盘报告分析结果自动生成调仓指令

执行时机: 周一开盘前
策略逻辑:
1. 读取当前持仓和目标配置
2. 根据权重偏差计算调仓数量
3. 生成交易指令
4. 保存为执行计划

目标配置(基于十五五规划+康波周期):
- 科创50ETF: 20% (成长科技)
- 创业板ETF: 15% (创新成长)
- 沪深300ETF: 15% (宽基核心)
- 中证1000ETF: 10% (中小盘)
- 华安黄金ETF: 15% (避险资产)
- 恒瑞医药: 10% (医药龙头)
- 中国神华: 已从目标中剔除(AI清仓信号)
"""

import os
import sys
import json
from datetime import datetime, timedelta

# 目标配置(调整后)
TARGET_WEIGHTS = {
    "588000": {"name": "科创50ETF", "weight": 0.20, "type": "ETF"},
    "159915": {"name": "创业板ETF", "weight": 0.15, "type": "ETF"},
    "510300": {"name": "沪深300ETF", "weight": 0.15, "type": "ETF"},
    "512100": {"name": "中证1000ETF", "weight": 0.10, "type": "ETF"},
    "518880": {"name": "华安黄金ETF", "weight": 0.15, "type": "ETF"},
    "600276": {"name": "恒瑞医药", "weight": 0.10, "type": "股票"},
    # 中国神华已从目标配置中剔除(AI清仓信号)
}

# 当前持仓(来自2026-06-12收盘报告)
CURRENT_POSITIONS = {
    "601088": {"name": "中国神华", "quantity": 3600, "price": 46.14},
    "600276": {"name": "恒瑞医药", "quantity": 2000, "price": 48.49},
    "510300": {"name": "沪深300ETF", "quantity": 4500, "price": 4.82},
    "512100": {"name": "中证1000ETF", "quantity": 4000, "price": 3.31},
    "588000": {"name": "科创50ETF", "quantity": 6000, "price": 1.76},
    "159915": {"name": "创业板ETF", "quantity": 3600, "price": 3.85},
    "518880": {"name": "华安黄金ETF", "quantity": 6600, "price": 8.66},
}

# 可用现金
AVAILABLE_CASH = 150000.0

def calculate_portfolio_value(positions):
    """计算当前持仓总市值"""
    total = 0.0
    for code, pos in positions.items():
        total += pos["quantity"] * pos["price"]
    return total

def generate_rebalance_plan(positions, target_weights, available_cash):
    """生成再平衡计划"""
    # 计算当前持仓市值
    current_value = calculate_portfolio_value(positions)
    total_capital = current_value + available_cash
    
    print("="*60)
    print("  再平衡策略分析")
    print(f"  日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print(f"  当前持仓市值: {current_value:,.2f}")
    print(f"  可用现金: {available_cash:,.2f}")
    print(f"  账户总值: {total_capital:,.2f}")
    print("="*60)
    
    # 计算每个标的的目标市值和当前市值
    plan = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "execution_date": get_next_monday(),
        "total_capital": total_capital,
        "current_value": current_value,
        "available_cash": available_cash,
        "instructions": [],
        "summary": {}
    }
    
    total_buy_amount = 0.0
    total_sell_amount = 0.0
    
    # 处理需要卖出的标的(中国神华)
    if "601088" in positions:
        pos = positions["601088"]
        sell_amount = pos["quantity"] * pos["price"]
        total_sell_amount += sell_amount
        plan["instructions"].append({
            "action": "SELL",
            "code": "601088",
            "name": pos["name"],
            "quantity": pos["quantity"],
            "price": pos["price"],
            "amount": sell_amount,
            "reason": "AI清仓信号: 政策落地，建议获利了结"
        })
    
    # 处理需要调整的标的
    for code, target in target_weights.items():
        current_pos = positions.get(code, {"quantity": 0, "price": 0})
        target_value = total_capital * target["weight"]
        current_value = current_pos["quantity"] * current_pos["price"]
        
        # 计算需要调整的金额
        diff_value = target_value - current_value
        
        if diff_value == 0:
            continue
        
        # 计算需要买卖的数量
        quantity = int(abs(diff_value) / current_pos["price"])
        
        if diff_value > 0:
            action = "BUY"
            amount = diff_value
            total_buy_amount += amount
            reason = f"低配 {target['weight']*100:.0f}%，需加仓"
        else:
            action = "SELL"
            amount = abs(diff_value)
            total_sell_amount += amount
            reason = f"高配 {target['weight']*100:.0f}%，需减仓"
        
        plan["instructions"].append({
            "action": action,
            "code": code,
            "name": target["name"],
            "quantity": quantity,
            "price": current_pos["price"],
            "amount": amount,
            "target_weight": target["weight"] * 100,
            "current_weight": (current_value / total_capital) * 100 if total_capital > 0 else 0,
            "reason": reason
        })
    
    # 计算交易后现金变化
    net_cash_flow = total_sell_amount - total_buy_amount
    final_cash = available_cash + net_cash_flow
    
    # 汇总信息
    plan["summary"] = {
        "total_sell_amount": total_sell_amount,
        "total_buy_amount": total_buy_amount,
        "net_cash_flow": net_cash_flow,
        "final_cash": final_cash,
        "trade_count": len(plan["instructions"]),
        "sell_count": sum(1 for i in plan["instructions"] if i["action"] == "SELL"),
        "buy_count": sum(1 for i in plan["instructions"] if i["action"] == "BUY"),
    }
    
    return plan

def get_next_monday():
    """获取下周一日期"""
    today = datetime.now()
    days_ahead = 0
    if today.weekday() == 0:  # 周一
        if datetime.now().hour < 9:  # 开盘前
            days_ahead = 0
        else:
            days_ahead = 7
    else:
        days_ahead = (7 - today.weekday()) % 7
    next_monday = today + timedelta(days=days_ahead)
    return next_monday.strftime("%Y-%m-%d")

def print_plan(plan):
    """打印再平衡计划"""
    print(f"\n执行日期: {plan['execution_date']}")
    print("\n交易指令汇总")
    print("-"*60)
    print(f"  卖出: {plan['summary']['sell_count']} 笔 | 金额: {plan['summary']['total_sell_amount']:,.2f}")
    print(f"  买入: {plan['summary']['buy_count']} 笔 | 金额: {plan['summary']['total_buy_amount']:,.2f}")
    print(f"  净现金流: {plan['summary']['net_cash_flow']:,.2f}")
    print(f"  交易后现金: {plan['summary']['final_cash']:,.2f}")
    print("-"*60)
    
    print("\n详细交易指令")
    print("-"*60)
    for i, instr in enumerate(plan["instructions"], 1):
        action_mark = "+" if instr["action"] == "BUY" else "-"
        print(f"\n  {i}. {action_mark} {instr['action']} {instr['name']} ({instr['code']})")
        print(f"     数量: {instr['quantity']} 股")
        print(f"     价格: {instr['price']:.2f}")
        print(f"     金额: {instr['amount']:,.2f}")
        if "target_weight" in instr:
            print(f"     当前权重: {instr['current_weight']:.2f}%")
            print(f"     目标权重: {instr['target_weight']:.0f}%")
        print(f"     原因: {instr['reason']}")
    
    print("\n" + "-"*60)
    print("操作提示: 建议在周一开盘后执行以上交易指令")
    print("风险提示: 实际成交价格可能与计划价格存在差异")

def save_plan(plan, filepath):
    """保存再平衡计划到文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"\n再平衡计划已保存: {filepath}")

def generate_md_report(plan):
    """生成Markdown格式报告"""
    lines = []
    lines.append("# 每周一再平衡策略报告")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 执行日期: {plan['execution_date']}")
    lines.append("")
    
    # 账户概况
    lines.append("## 一、账户概况")
    lines.append("")
    lines.append("| 指标 | 金额 |")
    lines.append("|:-----|-----:|")
    lines.append(f"| 当前持仓市值 | ¥ {plan['current_value']:,.2f} |")
    lines.append(f"| 可用现金 | ¥ {plan['available_cash']:,.2f} |")
    lines.append(f"| 账户总值 | ¥ {plan['total_capital']:,.2f} |")
    lines.append("")
    
    # 交易汇总
    lines.append("## 二、交易汇总")
    lines.append("")
    lines.append("| 类型 | 笔数 | 金额 |")
    lines.append("|:-----|-----:|-----:|")
    lines.append(f"| 卖出 | {plan['summary']['sell_count']} | ¥ {plan['summary']['total_sell_amount']:,.2f} |")
    lines.append(f"| 买入 | {plan['summary']['buy_count']} | ¥ {plan['summary']['total_buy_amount']:,.2f} |")
    lines.append(f"| 净现金流 | - | ¥ {plan['summary']['net_cash_flow']:,.2f} |")
    lines.append(f"| 交易后现金 | - | ¥ {plan['summary']['final_cash']:,.2f} |")
    lines.append("")
    
    # 详细指令
    lines.append("## 三、交易指令明细")
    lines.append("")
    
    # 卖出指令
    sells = [i for i in plan["instructions"] if i["action"] == "SELL"]
    if sells:
        lines.append("### 🔴 卖出指令")
        lines.append("")
        lines.append("| 序号 | 标的 | 代码 | 数量 | 价格 | 金额 | 原因 |")
        lines.append("|:-----|:-----|:-----|-----:|-----:|-----:|:-----|")
        for i, instr in enumerate(sells, 1):
            lines.append(f"| {i} | {instr['name']} | {instr['code']} | {instr['quantity']} | ¥ {instr['price']:.2f} | ¥ {instr['amount']:,.2f} | {instr['reason']} |")
        lines.append("")
    
    # 买入指令
    buys = [i for i in plan["instructions"] if i["action"] == "BUY"]
    if buys:
        lines.append("### 🟢 买入指令")
        lines.append("")
        lines.append("| 序号 | 标的 | 代码 | 数量 | 价格 | 金额 | 当前权重 | 目标权重 | 原因 |")
        lines.append("|:-----|:-----|:-----|-----:|-----:|-----:|---------:|---------:|:-----|")
        for i, instr in enumerate(buys, 1):
            lines.append(f"| {i} | {instr['name']} | {instr['code']} | {instr['quantity']} | ¥ {instr['price']:.2f} | ¥ {instr['amount']:,.2f} | {instr['current_weight']:.2f}% | {instr['target_weight']:.0f}% | {instr['reason']} |")
        lines.append("")
    
    # 目标配置
    lines.append("## 四、目标配置")
    lines.append("")
    lines.append("| 标的 | 代码 | 目标权重 |")
    lines.append("|:-----|:-----|---------:|")
    for code, target in TARGET_WEIGHTS.items():
        lines.append(f"| {target['name']} | {code} | {target['weight'] * 100:.0f}% |")
    lines.append("")
    
    # 备注
    lines.append("---")
    lines.append("")
    lines.append("**风险提示**: 实际成交价格可能与计划价格存在差异，请根据实时行情执行。")
    lines.append("**执行建议**: 建议在周一开盘后，根据市场情况分批执行。")
    lines.append("")
    
    return "\n".join(lines)

def save_md_report(content, filepath):
    """保存Markdown报告"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Markdown报告已保存: {filepath}")

if __name__ == "__main__":
    # 生成再平衡计划
    plan = generate_rebalance_plan(CURRENT_POSITIONS, TARGET_WEIGHTS, AVAILABLE_CASH)
    
    # 打印计划
    print_plan(plan)
    
    # 保存计划
    output_dir = r"E:\各种PY程序\每日报告归档\再平衡计划"
    os.makedirs(output_dir, exist_ok=True)
    
    # JSON格式
    json_path = os.path.join(output_dir, f"再平衡计划_{plan['execution_date']}.json")
    save_plan(plan, json_path)
    
    # Markdown格式
    md_content = generate_md_report(plan)
    md_path = os.path.join(output_dir, f"再平衡计划_{plan['execution_date']}.md")
    save_md_report(md_content, md_path)
    
    print(f"\n再平衡策略计划已生成，将于 {plan['execution_date']} 执行")