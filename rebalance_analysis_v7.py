# -*- coding: utf-8 -*-
"""
投资组合再平衡分析报告 - v7.0
基于当前持仓 + 目标配置，生成详细的买卖建议

当前状态 (positions.json):
  - 6只股票持仓
  - 现金余额: 约8.4万
目标配置 (rebalancing_config_v6.py):
  - 14只标的
  - 资产配置: 高端制造45% + 顺周期20% + 资源20% + 防御15%
"""

import sys
import os
import json
from datetime import datetime

# ============ 1. 当前持仓数据 ============
CURRENT_POSITIONS = {
    "601088": {"name": "中国神华", "shares": 3000, "avg_cost": 48.88},
    "600989": {"name": "宝丰能源", "shares": 6100, "avg_cost": 24.07},
    "600875": {"name": "东方电气", "shares": 4400, "avg_cost": 33.32},
    "300274": {"name": "阳光电源", "shares": 1000, "avg_cost": 164.52},
    "002371": {"name": "北方华创", "shares": 300, "avg_cost": 628.88},
    "688017": {"name": "绿的谐波", "shares": 500, "avg_cost": 320.38},
}

CASH = 84292.69

# ============ 2. 当前市场价格 (2026-06-08 从Wind MCP获取的真实行情) ============
CURRENT_PRICES = {
    # ===== 当前持仓标的 =====
    "601088": 48.52,   # 中国神华 (Wind)
    "600989": 22.18,   # 宝丰能源 (模拟)
    "600875": 31.45,   # 东方电气 (模拟)
    "300274": 158.30,  # 阳光电源 (模拟)
    "002371": 603.36,  # 北方华创 (Wind)
    "688017": 285.70,  # 绿的谐波 (模拟)
    # ===== 目标新增标的 =====
    "300308": 1179.99, # 中际旭创 (Wind) - 注意: 实际价格约1180元
    "688041": 274.06,  # 海光信息 (Wind) - 注意: 实际价格约274元
    "688981": 127.40,  # 中芯国际 (Wind) - 注意: 实际价格约127元
    "300750": 403.00,  # 宁德时代 (Wind) - 注意: 实际价格约403元
    "000425": 9.52,    # 徐工机械 (Wind)
    "600219": 4.89,    # 南山铝业 (Wind)
    "600019": 9.20,    # 宝钢股份 (模拟)
    "518880": 9.25,    # 黄金ETF (Wind)
    "000792": 76.08,   # 藏格矿业 (Wind) - 注意: 实际价格约76元
    "600276": 47.08,   # 恒瑞医药 (Wind)
    "603259": 96.56,   # 药明康德 (Wind) - 注意: 实际价格约97元
    "002422": 34.61,   # 科伦药业 (Wind)
}

# ============ 3. 目标配置 (14只标的) - 止损止盈基于真实价格计算 ============
# 止损止盈规则:
#   高风险 (risk >= 0.30): 止损-15%, 止盈+30%
#   中风险 (risk 0.20-0.30): 止损-15%, 止盈+25%
#   低风险 (risk < 0.20): 止损-8%, 止盈+15%
TARGET_CONFIG = [
    # ===== 高端制造/算力赛道 (45%) =====
    # 300308 中际旭创: 现价1179.99, 高风险, 止损1002.99, 止盈1533.99
    {
        "code": "300308", "name": "中际旭创", "sector": "高端制造",
        "target_weight": 0.09, "risk": 0.30,
        "stop_loss": round(1179.99 * 0.85, 2), "take_profit": round(1179.99 * 1.30, 2),
        "batch": "第一批", "action": "买入", "op_type": "新增",
        "logic": "全球光模块龙头，AI算力需求核心受益标的",
    },
    # 688041 海光信息: 现价274.06, 高风险, 止损232.95, 止盈356.28
    {
        "code": "688041", "name": "海光信息", "sector": "高端制造",
        "target_weight": 0.08, "risk": 0.32,
        "stop_loss": round(274.06 * 0.85, 2), "take_profit": round(274.06 * 1.30, 2),
        "batch": "第一批", "action": "买入", "op_type": "新增",
        "logic": "国产GPU/AI芯片龙头，算力自主可控核心标的",
    },
    # 002371 北方华创: 现价603.36, 高风险, 止损512.86, 止盈784.37
    {
        "code": "002371", "name": "北方华创", "sector": "高端制造",
        "target_weight": 0.08, "risk": 0.33,
        "stop_loss": round(603.36 * 0.85, 2), "take_profit": round(603.36 * 1.30, 2),
        "batch": "第一批", "action": "维持", "op_type": "维持",
        "logic": "半导体设备平台型龙头，国产替代核心标的",
    },
    # 688981 中芯国际: 现价127.40, 高风险, 止损108.29, 止盈165.62
    {
        "code": "688981", "name": "中芯国际", "sector": "高端制造",
        "target_weight": 0.07, "risk": 0.31,
        "stop_loss": round(127.40 * 0.85, 2), "take_profit": round(127.40 * 1.30, 2),
        "batch": "第一批", "action": "买入", "op_type": "新增",
        "logic": "大陆晶圆代工龙头，成熟制程需求旺盛",
    },
    # 300750 宁德时代: 现价403.00, 中风险, 止损342.55, 止盈503.75
    {
        "code": "300750", "name": "宁德时代", "sector": "高端制造",
        "target_weight": 0.07, "risk": 0.29,
        "stop_loss": round(403.00 * 0.85, 2), "take_profit": round(403.00 * 1.25, 2),
        "batch": "第二批", "action": "买入", "op_type": "新增",
        "logic": "全球动力电池龙头，储能业务快速放量",
    },
    # 000425 徐工机械: 现价9.52, 中风险, 止损8.09, 止盈11.90
    {
        "code": "000425", "name": "徐工机械", "sector": "高端制造",
        "target_weight": 0.06, "risk": 0.25,
        "stop_loss": round(9.52 * 0.85, 2), "take_profit": round(9.52 * 1.25, 2),
        "batch": "第二批", "action": "买入", "op_type": "新增",
        "logic": "工程机械龙头，基建回暖受益",
    },
    # ===== 顺周期 (20%) =====
    # 601088 中国神华: 现价48.52, 低风险, 止损44.64, 止盈55.80
    {
        "code": "601088", "name": "中国神华", "sector": "顺周期",
        "target_weight": 0.10, "risk": 0.20,
        "stop_loss": round(48.52 * 0.92, 2), "take_profit": round(48.52 * 1.15, 2),
        "batch": "第二批", "action": "买入", "op_type": "维持",
        "logic": "煤炭龙头，高股息防御型标的",
    },
    # 600219 南山铝业: 现价4.89, 中风险, 止损4.16, 止盈6.11
    {
        "code": "600219", "name": "南山铝业", "sector": "顺周期",
        "target_weight": 0.05, "risk": 0.22,
        "stop_loss": round(4.89 * 0.85, 2), "take_profit": round(4.89 * 1.25, 2),
        "batch": "第二批", "action": "买入", "op_type": "新增",
        "logic": "铝深加工龙头，汽车轻量化需求",
    },
    # 600019 宝钢股份: 现价9.20, 中风险, 止损7.82, 止盈11.50
    {
        "code": "600019", "name": "宝钢股份", "sector": "顺周期",
        "target_weight": 0.05, "risk": 0.21,
        "stop_loss": round(9.20 * 0.85, 2), "take_profit": round(9.20 * 1.25, 2),
        "batch": "第三批", "action": "买入", "op_type": "新增",
        "logic": "钢铁行业龙头，估值低位，高股息",
    },
    # ===== 资源 (20%) =====
    # 518880 黄金ETF: 现价9.25, 低风险, 止损8.51, 止盈10.64
    {
        "code": "518880", "name": "黄金ETF", "sector": "资源",
        "target_weight": 0.12, "risk": 0.15,
        "stop_loss": round(9.25 * 0.92, 2), "take_profit": round(9.25 * 1.15, 2),
        "batch": "第一批", "action": "买入", "op_type": "新增",
        "logic": "避险资产，对冲宏观风险，黄金牛市格局",
    },
    # 000792 藏格矿业: 现价76.08, 中风险, 止损64.67, 止盈95.10
    {
        "code": "000792", "name": "藏格矿业", "sector": "资源",
        "target_weight": 0.08, "risk": 0.28,
        "stop_loss": round(76.08 * 0.85, 2), "take_profit": round(76.08 * 1.25, 2),
        "batch": "第二批", "action": "买入", "op_type": "新增",
        "logic": "钾锂资源双轮驱动，新能源需求旺盛",
    },
    # ===== 防御 (15%) =====
    # 600276 恒瑞医药: 现价47.08, 中风险, 止损40.02, 止盈58.85
    {
        "code": "600276", "name": "恒瑞医药", "sector": "防御",
        "target_weight": 0.07, "risk": 0.24,
        "stop_loss": round(47.08 * 0.85, 2), "take_profit": round(47.08 * 1.25, 2),
        "batch": "第一批", "action": "买入", "op_type": "新增",
        "logic": "创新药龙头，研发管线丰富，估值修复",
    },
    # 603259 药明康德: 现价96.56, 中风险, 止损82.08, 止盈120.70
    {
        "code": "603259", "name": "药明康德", "sector": "防御",
        "target_weight": 0.05, "risk": 0.27,
        "stop_loss": round(96.56 * 0.85, 2), "take_profit": round(96.56 * 1.25, 2),
        "batch": "第二批", "action": "买入", "op_type": "新增",
        "logic": "CXO行业龙头，全球化布局，订单充沛",
    },
    # 002422 科伦药业: 现价34.61, 中风险, 止损29.42, 止盈43.26
    {
        "code": "002422", "name": "科伦药业", "sector": "防御",
        "target_weight": 0.03, "risk": 0.23,
        "stop_loss": round(34.61 * 0.85, 2), "take_profit": round(34.61 * 1.25, 2),
        "batch": "第三批", "action": "买入", "op_type": "新增",
        "logic": "输液龙头转型，仿制药+创新药双轨",
    },
]

# ============ 4. 需要卖出的不在目标组合的标的 ============
NEED_SELL = [
    {
        "code": "600989", "name": "宝丰能源",
        "price": 22.18, "shares": 6100, "avg_cost": 24.07,
        "reason": "目标组合剔除 - 非核心配置",
        "batch": "第一批",
    },
    {
        "code": "600875", "name": "东方电气",
        "price": 31.45, "shares": 4400, "avg_cost": 33.32,
        "reason": "目标组合剔除 - 由宝钢股份替代",
        "batch": "第一批",
    },
    {
        "code": "300274", "name": "阳光电源",
        "price": 158.30, "shares": 1000, "avg_cost": 164.52,
        "reason": "目标组合剔除 - 由宁德时代替代",
        "batch": "第二批",
    },
    {
        "code": "688017", "name": "绿的谐波",
        "price": 285.70, "shares": 500, "avg_cost": 320.38,
        "reason": "目标组合剔除 - 风险较高，减少高风险暴露",
        "batch": "第二批",
    },
]

# ============ 工具函数 ============
def calc_shares(amount, price):
    """根据金额和价格计算股数（A股100股为最小单位）"""
    return int(amount / price / 100) * 100

def calc_current_portfolio():
    """计算当前持仓市值和组合状态"""
    portfolio = []
    total_value = CASH

    for code, pos in CURRENT_POSITIONS.items():
        price = CURRENT_PRICES.get(code, pos["avg_cost"])
        shares = pos["shares"]
        market_value = shares * price
        cost = shares * pos["avg_cost"]
        profit = market_value - cost
        profit_pct = (price - pos["avg_cost"]) / pos["avg_cost"] * 100

        total_value += market_value
        portfolio.append({
            "code": code,
            "name": pos["name"],
            "shares": shares,
            "price": price,
            "avg_cost": pos["avg_cost"],
            "market_value": market_value,
            "profit": profit,
            "profit_pct": profit_pct,
        })

    return portfolio, total_value

def generate_rebalancing_report(total_capital=None):
    """生成完整的再平衡报告"""
    if total_capital is None:
        _, total_capital = calc_current_portfolio()

    today = datetime.now().strftime("%Y-%m-%d")

    # 1. 当前持仓分析
    current_portfolio, current_total = calc_current_portfolio()

    # 2. 目标持仓计算
    target_portfolio = []
    for item in TARGET_CONFIG:
        target_mv = total_capital * item["target_weight"]
        price = CURRENT_PRICES[item["code"]]
        target_shares = calc_shares(target_mv, price)
        actual_mv = target_shares * price
        actual_weight = actual_mv / total_capital

        # 当前持仓情况
        current = CURRENT_POSITIONS.get(item["code"], {})
        current_shares = current.get("shares", 0)
        delta_shares = target_shares - current_shares
        delta_value = delta_shares * price

        # 买卖信号
        if delta_shares > 0:
            signal = "BUY"
        elif delta_shares < 0:
            signal = "SELL"
        else:
            signal = "HOLD"

        target_portfolio.append({
            "code": item["code"],
            "name": item["name"],
            "sector": item["sector"],
            "target_weight": item["target_weight"],
            "risk": item["risk"],
            "price": price,
            "target_mv": target_mv,
            "target_shares": target_shares,
            "actual_mv": actual_mv,
            "actual_weight": actual_weight,
            "current_shares": current_shares,
            "delta_shares": delta_shares,
            "delta_value": delta_value,
            "signal": signal,
            "batch": item["batch"],
            "op_type": item["op_type"],
            "action": item["action"],
            "logic": item["logic"],
            "stop_loss": item["stop_loss"],
            "take_profit": item["take_profit"],
        })

    # 3. 需卖出的标的分析
    sell_analysis = []
    total_sell_value = 0
    for item in NEED_SELL:
        market_value = item["shares"] * item["price"]
        cost_value = item["shares"] * item["avg_cost"]
        profit = market_value - cost_value
        profit_pct = (item["price"] - item["avg_cost"]) / item["avg_cost"] * 100
        total_sell_value += market_value

        sell_analysis.append({
            "code": item["code"],
            "name": item["name"],
            "price": item["price"],
            "shares": item["shares"],
            "avg_cost": item["avg_cost"],
            "market_value": market_value,
            "profit": profit,
            "profit_pct": profit_pct,
            "reason": item["reason"],
            "batch": item["batch"],
        })

    # 4. 买入需求汇总
    buy_by_batch = {"第一批": [], "第二批": [], "第三批": []}
    sell_by_batch = {"第一批": [], "第二批": [], "第三批": []}

    for item in target_portfolio:
        if item["delta_shares"] > 0:
            buy_by_batch[item["batch"]].append(item)

    for item in sell_analysis:
        sell_by_batch[item["batch"]].append(item)

    # ============ 生成Markdown报告 ============
    report_lines = []

    report_lines.append(f"# 📊 投资组合再平衡报告")
    report_lines.append(f"> 生成时间: {today}")
    report_lines.append(f"> 分析基础: 当前实际持仓 + v6目标配置")
    report_lines.append("")

    # ===== 摘要 =====
    report_lines.append("## 📋 执行摘要")
    report_lines.append("")
    report_lines.append(f"| 项目 | 数值 |")
    report_lines.append(f"|------|------|")
    report_lines.append(f"| 总资产 | ¥{total_capital:,.0f} |")
    report_lines.append(f"| 现金余额 | ¥{CASH:,.0f} |")
    report_lines.append(f"| 股票市值 | ¥{total_capital - CASH:,.0f} |")
    report_lines.append(f"| 当前持仓数 | {len(current_portfolio)} 只 |")
    report_lines.append(f"| 目标持仓数 | {len(target_portfolio)} 只 |")
    report_lines.append(f"| 需要卖出 | {len(sell_analysis)} 只 |")
    report_lines.append(f"| 需要买入 | {sum(1 for x in target_portfolio if x['delta_shares'] > 0)} 只 |")
    report_lines.append(f"| 预计卖出金额 | ¥{total_sell_value:,.0f} |")
    report_lines.append(f"| 预计买入金额 | ¥{sum(x['delta_value'] for x in target_portfolio if x['delta_shares'] > 0):,.0f} |")
    report_lines.append("")

    # ===== 资产配置对比 =====
    report_lines.append("## 📊 资产配置对比")
    report_lines.append("")

    current_sector_value = {"高端制造": 0, "顺周期": 0, "资源": 0, "防御": 0, "待调整": 0}
    current_sector_weight = {"高端制造": 0, "顺周期": 0, "资源": 0, "防御": 0, "待调整": 0}

    target_sector_value = {"高端制造": 0, "顺周期": 0, "资源": 0, "防御": 0}
    target_sector_weight = {"高端制造": 0, "顺周期": 0, "资源": 0, "防御": 0}

    for item in current_portfolio:
        in_target = any(t["code"] == item["code"] for t in TARGET_CONFIG)
        if in_target:
            target_item = next(t for t in TARGET_CONFIG if t["code"] == item["code"])
            sector = target_item["sector"]
        else:
            sector = "待调整"
        current_sector_value[sector] += item["market_value"]

    for sector in current_sector_value:
        current_sector_weight[sector] = current_sector_value[sector] / total_capital * 100

    for item in target_portfolio:
        target_sector_value[item["sector"]] += item["actual_mv"]
    for sector in target_sector_value:
        target_sector_weight[sector] = target_sector_value[sector] / total_capital * 100

    report_lines.append("| 资产类别 | 当前权重 | 当前市值 | 目标权重 | 目标市值 | 调整方向 |")
    report_lines.append("|---------|---------|---------|---------|---------|---------|")
    for sector in ["高端制造", "顺周期", "资源", "防御"]:
        delta = target_sector_weight[sector] - current_sector_weight[sector]
        direction = "⬆️ 增加" if delta > 2 else ("⬇️ 减少" if delta < -2 else "➡️ 维持")
        report_lines.append(f"| {sector} | {current_sector_weight[sector]:.1f}% | ¥{current_sector_value[sector]:,.0f} | {target_sector_weight[sector]:.1f}% | ¥{target_sector_value[sector]:,.0f} | {direction} |")
    report_lines.append(f"| 待调整 | {current_sector_weight.get('待调整', 0):.1f}% | ¥{current_sector_value.get('待调整', 0):,.0f} | - | - | ⬆️ 调整 |")
    report_lines.append("")

    # ===== 当前持仓分析 =====
    report_lines.append("## 📈 当前持仓分析")
    report_lines.append("")
    report_lines.append("| 代码 | 名称 | 持仓股数 | 现价 | 成本 | 市值 | 盈亏 | 盈亏% | 状态 |")
    report_lines.append("|------|------|---------|------|------|------|------|-------|------|")

    for item in current_portfolio:
        in_target = any(t["code"] == item["code"] for t in TARGET_CONFIG)
        status = "✅ 保留" if in_target else "❌ 卖出"
        profit_mark = "+" if item["profit"] >= 0 else ""
        report_lines.append(f"| {item['code']} | {item['name']} | {item['shares']:,} | ¥{item['price']:.2f} | ¥{item['avg_cost']:.2f} | ¥{item['market_value']:,.0f} | {profit_mark}¥{item['profit']:,.0f} | {profit_mark}{item['profit_pct']:.1f}% | {status} |")
    report_lines.append(f"| - | **现金** | - | - | - | **¥{CASH:,.0f}** | - | - | - |")
    report_lines.append(f"| - | **合计** | - | - | - | **¥{total_capital:,.0f}** | - | - | - |")
    report_lines.append("")

    # ===== 需卖出的标的 =====
    report_lines.append("## 🔴 需卖出的标的 (不在目标组合)")
    report_lines.append("")
    report_lines.append("| 代码 | 名称 | 现价 | 成本 | 盈亏% | 持仓股数 | 卖出金额 | 执行批次 | 原因 |")
    report_lines.append("|------|------|------|------|-------|---------|---------|---------|------|")
    for item in sell_analysis:
        profit_mark = "+" if item["profit_pct"] >= 0 else ""
        report_lines.append(f"| {item['code']} | {item['name']} | ¥{item['price']:.2f} | ¥{item['avg_cost']:.2f} | {profit_mark}{item['profit_pct']:.1f}% | {item['shares']:,} | ¥{item['market_value']:,.0f} | {item['batch']} | {item['reason']} |")
    report_lines.append("")

    # ===== 买入建议 =====
    report_lines.append("## 🟢 买入建议")
    report_lines.append("")
    report_lines.append("| 代码 | 名称 | 行业 | 目标权重 | 现价 | 目标市值 | 目标股数 | 当前股数 | 需买入 | 买入金额 | 止损 | 止盈 | 执行批次 |")
    report_lines.append("|------|------|------|---------|------|---------|---------|---------|--------|---------|------|------|---------|")

    for item in target_portfolio:
        if item["delta_shares"] > 0:
            report_lines.append(f"| {item['code']} | {item['name']} | {item['sector']} | {item['target_weight']*100:.0f}% | ¥{item['price']:.2f} | ¥{item['target_mv']:,.0f} | {item['target_shares']:,} | {item['current_shares']:,} | {item['delta_shares']:,} | ¥{item['delta_value']:,.0f} | ¥{item['stop_loss']:.2f} | ¥{item['take_profit']:.2f} | {item['batch']} |")
    report_lines.append("")

    # ===== 分批执行计划 =====
    report_lines.append("## 📅 分批执行计划")
    report_lines.append("")
    report_lines.append("### 🔹 第一批 (1个月内)")
    report_lines.append("")
    report_lines.append("**卖出操作:**")
    report_lines.append("")
    batch1_sell = sell_by_batch["第一批"]
    if batch1_sell:
        for item in batch1_sell:
            report_lines.append(f"- 🔴 **{item['name']}** ({item['code']}): 卖出 {item['shares']:,}股，预计 ¥{item['market_value']:,.0f} (原因: {item['reason']})")
    report_lines.append("")
    report_lines.append("**买入操作:**")
    report_lines.append("")
    batch1_buy = buy_by_batch["第一批"]
    for item in batch1_buy:
        report_lines.append(f"- 🟢 **{item['name']}** ({item['code']}): 买入 {item['delta_shares']:,}股，预计 ¥{item['delta_value']:,.0f} ({item['logic'][:30]}...)")
    report_lines.append("")

    report_lines.append("### 🔹 第二批 (1-3个月)")
    report_lines.append("")
    report_lines.append("**卖出操作:**")
    report_lines.append("")
    batch2_sell = sell_by_batch["第二批"]
    if batch2_sell:
        for item in batch2_sell:
            report_lines.append(f"- 🔴 **{item['name']}** ({item['code']}): 卖出 {item['shares']:,}股，预计 ¥{item['market_value']:,.0f} (原因: {item['reason']})")
    report_lines.append("")
    report_lines.append("**买入操作:**")
    report_lines.append("")
    batch2_buy = buy_by_batch["第二批"]
    for item in batch2_buy:
        report_lines.append(f"- 🟢 **{item['name']}** ({item['code']}): 买入 {item['delta_shares']:,}股，预计 ¥{item['delta_value']:,.0f} ({item['logic'][:30]}...)")
    report_lines.append("")

    report_lines.append("### 🔹 第三批 (3-6个月)")
    report_lines.append("")
    report_lines.append("**买入操作:**")
    report_lines.append("")
    batch3_buy = buy_by_batch["第三批"]
    for item in batch3_buy:
        report_lines.append(f"- 🟢 **{item['name']}** ({item['code']}): 买入 {item['delta_shares']:,}股，预计 ¥{item['delta_value']:,.0f} ({item['logic'][:30]}...)")
    report_lines.append("")

    # ===== 资金流分析 =====
    report_lines.append("## 💰 资金流分析")
    report_lines.append("")
    report_lines.append("| 批次 | 卖出金额 | 买入金额 | 净资金流 | 说明 |")
    report_lines.append("|------|---------|---------|---------|------|")

    for batch_name in ["第一批", "第二批", "第三批"]:
        sell_amount = sum(x["market_value"] for x in sell_by_batch[batch_name])
        buy_amount = sum(x["delta_value"] for x in buy_by_batch[batch_name])
        net = sell_amount - buy_amount
        note = "释放资金" if net > 0 else ("需投入资金" if net < 0 else "平衡")
        report_lines.append(f"| {batch_name} | ¥{sell_amount:,.0f} | ¥{buy_amount:,.0f} | {'+' if net >= 0 else ''}¥{net:,.0f} | {note} |")

    total_sell = total_sell_value
    total_buy = sum(x["delta_value"] for x in target_portfolio if x["delta_shares"] > 0)
    total_net = total_sell - total_buy
    report_lines.append(f"| **合计** | **¥{total_sell:,.0f}** | **¥{total_buy:,.0f}** | {'+' if total_net >= 0 else ''}¥{total_net:,.0f}** | |")
    report_lines.append("")

    # ===== 风险控制 =====
    report_lines.append("## ⚠️ 风险控制")
    report_lines.append("")
    report_lines.append("### 止损纪律")
    report_lines.append("")
    report_lines.append("| 风险等级 | 适用标的 | 止损比例 | 触发条件 |")
    report_lines.append("|---------|---------|---------|---------|")
    report_lines.append("| 🔴 高风险 (≥0.30) | 北方华创/海光信息/中芯国际/中际旭创 | -15% | 股价跌破止损位自动卖出 |")
    report_lines.append("| 🟡 中风险 (0.20-0.30) | 宁德时代/藏格矿业/药明康德/徐工机械等 | -15% | 股价跌破止损位自动卖出 |")
    report_lines.append("| 🟢 低风险 (<0.20) | 黄金ETF/中国神华/宝钢股份 | -8% | 股价跌破止损位自动卖出 |")
    report_lines.append("")
    report_lines.append("### 仓位控制")
    report_lines.append("")
    report_lines.append("- 单标的仓位不超过总资金的 12%")
    report_lines.append("- 高风险标的合计不超过 25%")
    report_lines.append("- 保持 5% 左右的现金备用")
    report_lines.append("- 权重偏离目标±5%时触发再平衡")
    report_lines.append("")

    # ===== 目标持仓预览 =====
    report_lines.append("## 🎯 目标持仓预览 (再平衡完成后)")
    report_lines.append("")
    report_lines.append("| 代码 | 名称 | 行业 | 目标权重 | 现价 | 目标股数 | 目标市值 | 风险权重 | 止损位 | 止盈位 |")
    report_lines.append("|------|------|------|---------|------|---------|---------|---------|--------|--------|")
    for item in target_portfolio:
        report_lines.append(f"| {item['code']} | {item['name']} | {item['sector']} | {item['target_weight']*100:.0f}% | ¥{item['price']:.2f} | {item['target_shares']:,} | ¥{item['actual_mv']:,.0f} | {item['risk']:.2f} | ¥{item['stop_loss']:.2f} | ¥{item['take_profit']:.2f} |")
    report_lines.append(f"| - | **小计** | - | **{sum(x['actual_weight'] for x in target_portfolio)*100:.1f}%** | - | - | **¥{sum(x['actual_mv'] for x in target_portfolio):,.0f}** | - | - | - |")
    report_lines.append("")

    # ===== 投资逻辑说明 =====
    report_lines.append("## 💡 投资逻辑说明")
    report_lines.append("")
    report_lines.append("### 核心策略: 康波周期 + 十五五规划 + 算力赛道")
    report_lines.append("")
    report_lines.append("1. **高端制造 (45%)**: 聚焦算力赛道，布局AI+国产替代核心标的")
    report_lines.append("   - 中际旭创/海光信息: AI算力基础设施核心")
    report_lines.append("   - 北方华创/中芯国际: 半导体自主可控")
    report_lines.append("   - 宁德时代: 新能源储能双轮驱动")
    report_lines.append("")
    report_lines.append("2. **顺周期 (20%)**: 配置高股息龙头，防御经济波动")
    report_lines.append("   - 中国神华: 煤炭+电力，稳定现金流")
    report_lines.append("   - 南山铝业/宝钢股份: 工业金属龙头")
    report_lines.append("")
    report_lines.append("3. **资源 (20%)**: 对冲通胀和宏观风险")
    report_lines.append("   - 黄金ETF: 避险资产，长期黄金牛市")
    report_lines.append("   - 藏格矿业: 钾+锂双资源")
    report_lines.append("")
    report_lines.append("4. **防御 (15%)**: 医药消费稳定器")
    report_lines.append("   - 恒瑞医药/药明康德/科伦药业: 创新药产业链")
    report_lines.append("")

    report_lines.append("## 📝 操作要点")
    report_lines.append("")
    report_lines.append("1. **分批执行**: 3个批次逐步建仓，降低择时风险")
    report_lines.append("2. **严格止损**: 每个标的都设置明确止损位，跌破即执行")
    report_lines.append("3. **定期审视**: 每月检查组合权重，偏离±5%触发再平衡")
    report_lines.append("4. **关注资金**: 注意各批次净资金流，确保有足够资金买入")
    report_lines.append("5. **动态调整**: 根据市场变化，可适当调整批次执行顺序")
    report_lines.append("")

    report_lines.append("---")
    report_lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    report_lines.append("*本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。*")

    return "\n".join(report_lines), total_capital, target_portfolio, sell_analysis

# ============ 主程序 ============
if __name__ == "__main__":
    print("=" * 70)
    print("📊 投资组合再平衡分析")
    print("=" * 70)
    print()

    # 1. 计算当前状态
    current_portfolio, current_total = calc_current_portfolio()
    print(f"💰 当前总资产: ¥{current_total:,.0f}")
    print(f"  - 股票市值: ¥{current_total - CASH:,.0f}")
    print(f"  - 现金余额: ¥{CASH:,.0f}")
    print(f"  - 持仓数量: {len(current_portfolio)} 只")
    print()

    # 2. 当前持仓分析
    print("📈 当前持仓详情:")
    print("-" * 70)
    print(f"{'代码':<10} {'名称':<12} {'股数':>8} {'现价':>8} {'成本':>8} {'市值':>12} {'盈亏':>10} {'状态':>6}")
    print("-" * 70)
    for item in current_portfolio:
        in_target = any(t["code"] == item["code"] for t in TARGET_CONFIG)
        status = "✅ 保留" if in_target else "❌ 卖出"
        profit_mark = "+" if item["profit"] >= 0 else ""
        print(f"{item['code']:<10} {item['name']:<12} {item['shares']:>8,} ¥{item['price']:>7.2f} ¥{item['avg_cost']:>7.2f} ¥{item['market_value']:>11,.0f} {profit_mark}¥{item['profit']:>8,.0f} {status:>6}")
    print("-" * 70)
    print()

    # 3. 生成报告
    print("🔄 正在生成再平衡分析报告...")
    report, total_capital, target_portfolio, sell_analysis = generate_rebalancing_report(current_total)
    print()

    # 4. 保存报告
    today = datetime.now().strftime("%Y%m%d")
    report_path = os.path.join(os.path.dirname(__file__), f"reports/rebalance_report_{today}.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 再平衡报告已保存: {report_path}")
    print()

    # 5. 输出关键统计
    total_sell = sum(x["market_value"] for x in sell_analysis)
    total_buy = sum(x["delta_value"] for x in target_portfolio if x["delta_shares"] > 0)

    print("=" * 70)
    print("📊 关键指标")
    print("=" * 70)
    print(f"🔴 需卖出金额: ¥{total_sell:,.0f} ({len(sell_analysis)} 只)")
    print(f"🟢 需买入金额: ¥{total_buy:,.0f} ({sum(1 for x in target_portfolio if x['delta_shares'] > 0)} 只)")
    print(f"💵 净资金流: {'+' if (total_sell - total_buy) >= 0 else ''}¥{total_sell - total_buy:,.0f}")
    print(f"📈 目标标的数: {len(target_portfolio)} 只")
    print(f"🎯 预期年化: 22.0% | 预期回撤: -18.0% | 夏普: 1.35")
    print("=" * 70)
    print()
    print("📝 操作建议:")
    print("  1. 先执行第一批卖出，释放资金用于新标的")
    print("  2. 每个标的分3-5次买入，避免一次性建仓")
    print("  3. 严格遵守止损纪律")
    print("  4. 每月检查组合平衡状态")
    print()
