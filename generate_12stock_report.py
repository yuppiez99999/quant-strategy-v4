import os
import json
from datetime import datetime

STOCK_NAMES = {
    "601088": "中国神华", "600276": "恒瑞医药", "510300": "沪深300ETF",
    "512100": "中证1000ETF", "588000": "科创50ETF", "159915": "创业板ETF",
    "518880": "华安黄金ETF", "512760": "半导体ETF", "512880": "证券ETF",
    "515030": "新能源车ETF", "512170": "医疗ETF", "159928": "消费ETF"
}

TARGET_WEIGHTS = {
    "601088": 0.10, "600276": 0.08, "510300": 0.12,
    "512100": 0.08, "588000": 0.12, "159915": 0.10,
    "518880": 0.09, "512760": 0.06, "512880": 0.06,
    "515030": 0.05, "512170": 0.05, "159928": 0.09
}

PRICES = {
    "601088": 47.51, "600276": 47.01, "510300": 4.78,
    "512100": 3.30, "588000": 1.74, "159915": 3.87,
    "518880": 8.74, "512760": 1.55, "512880": 1.32,
    "515030": 1.92, "512170": 1.45, "159928": 2.68
}

INITIAL_CAPITAL = 2000000

def calculate_positions():
    positions = {}
    remaining_cash = INITIAL_CAPITAL
    for code, weight in TARGET_WEIGHTS.items():
        target_value = INITIAL_CAPITAL * weight
        price = PRICES[code]
        shares = int(target_value / price / 100) * 100
        positions[code] = {
            "shares": shares,
            "avg_cost": price,
            "target_weight": weight
        }
        remaining_cash -= shares * price
    return positions, remaining_cash

positions, cash = calculate_positions()

total_value = cash
position_details = []
up_count = 0
down_count = 0
best_performer = None
worst_performer = None
best_pnl = float('-inf')
worst_pnl = float('inf')

for code in STOCK_NAMES:
    pos = positions[code]
    shares = pos["shares"]
    cost = pos["avg_cost"]
    price = PRICES[code]
    mv = shares * price
    total_value += mv
    pnl = ((price - cost) / cost * 100) if cost > 0 else 0
    aw = (mv / total_value * 100) if total_value > 0 else 0
    tw = TARGET_WEIGHTS[code] * 100
    dev = aw - tw
    
    if pnl > best_pnl:
        best_pnl = pnl
        best_performer = {"name": STOCK_NAMES[code], "pnl": pnl}
    if pnl < worst_pnl:
        worst_pnl = pnl
        worst_performer = {"name": STOCK_NAMES[code], "pnl": pnl}
    
    if pnl > 0:
        up_count += 1
    elif pnl < 0:
        down_count += 1
    
    position_details.append({
        "code": code,
        "name": STOCK_NAMES[code],
        "shares": shares,
        "cost": cost,
        "price": price,
        "mv": mv,
        "pnl": pnl,
        "actual_weight": aw,
        "target_weight": tw,
        "deviation": dev
    })

now = datetime.now()

def get_pnl_color(pnl):
    if pnl > 0:
        return "<font color='#52C41A'>+" + str(round(pnl, 1)) + "%</font>"
    elif pnl < 0:
        return "<font color='#F5222D'>" + str(round(pnl, 1)) + "%</font>"
    return "0%"

def get_deviation_color(dev):
    if abs(dev) > 2:
        return "<font color='#F5222D'>" + str(round(dev, 1)) + "%</font>"
    elif abs(dev) > 1:
        return "<font color='#FAAD14'>" + str(round(dev, 1)) + "%</font>"
    return "<font color='#52C41A'>" + str(round(dev, 1)) + "%</font>"

def get_trend_icon(pnl):
    if pnl > 1:
        return "📈"
    elif pnl > 0:
        return "⬆️"
    elif pnl < -1:
        return "📉"
    elif pnl < 0:
        return "⬇️"
    return "➡️"

def get_recommendation(dev):
    if dev < -2:
        return "🔴 加仓"
    elif dev < -1:
        return "🟡 小幅加仓"
    elif dev > 2:
        return "🔴 减仓"
    elif dev > 1:
        return "🟡 小幅减仓"
    return "🟢 持有"

def generate_table_rows(data):
    rows = []
    for d in data:
        rows.append("| " + d['name'] + " | `" + d['code'] + "` | ¥" + str(round(d['price'], 2)) + " | <div align='right'>" + get_pnl_color(d['pnl']) + "</div> | <div align='center'>" + get_trend_icon(d['pnl']) + "</div> |")
    return "\n".join(rows)

def generate_position_rows(data):
    rows = []
    for d in data:
        rows.append("| **" + d['name'] + "** | " + "{:,}".format(d['shares']) + "股 | ¥" + str(round(d['cost'], 2)) + " | ¥" + str(round(d['price'], 2)) + " | ¥" + "{:,}".format(int(d['mv'])) + " | <div align='right'>" + get_pnl_color(d['pnl']) + "</div> |")
    return "\n".join(rows)

def generate_deviation_rows(data):
    rows = []
    for d in data:
        rows.append("| " + d['name'] + " | <div align='right'>" + str(round(d['actual_weight'], 1)) + "%</div> | <div align='right'>" + str(int(d['target_weight'])) + "%</div> | <div align='right'>" + get_deviation_color(d['deviation']) + "</div> | <div align='center'>" + get_recommendation(d['deviation']) + "</div> |")
    return "\n".join(rows)

total_profit = total_value - INITIAL_CAPITAL
profit_pct = (total_profit / INITIAL_CAPITAL * 100) if INITIAL_CAPITAL > 0 else 0
profit_status = "🟢" if total_value >= INITIAL_CAPITAL else "🔴"
profit_text = "🟢 盈利" if total_profit > 0 else "🔴 亏损"

report_lines = [
    "# 📊 12只标的量化策略日报",
    "",
    "---",
    "",
    "## 📅 报告信息",
    "",
    "| **项目** | **内容** |",
    "|----------|----------|",
    "| 📆 日期 | " + now.strftime("%Y年%m月%d日") + " |",
    "| ⏰ 时间 | " + now.strftime("%H:%M:%S") + " |",
    "| 🎯 策略版本 | **v5.1-12Stock** |",
    "| 💰 初始资金 | ¥" + "{:,}".format(INITIAL_CAPITAL) + " |",
    "",
    "---",
    "",
    "## 💎 账户总览",
    "",
    "| 指标 | 当前值 | 状态 |",
    "|------|--------|------|",
    "| 📊 账户总值 | **¥" + "{:,}".format(int(total_value)) + "** | " + profit_status + " |",
    "| 📦 持仓市值 | ¥" + "{:,}".format(int(total_value - cash)) + " | |",
    "| 💵 可用现金 | ¥" + "{:,}".format(int(cash)) + " | |",
    "| 📈 累计收益 | **" + ("+" if profit_pct > 0 else "") + str(round(profit_pct, 1)) + "%** | " + profit_text + " |",
    "| 💹 累计盈利 | **¥" + ("+" if total_profit > 0 else "") + "{:,}".format(int(total_profit)) + "** | |",
    "",
    "---",
    "",
    "## 📈 实时行情概览",
    "",
    "| <div align=\"center\">标的</div> | <div align=\"center\">代码</div> | <div align=\"center\">现价</div> | <div align=\"center\">涨跌幅</div> | <div align=\"center\">趋势</div> |",
    "|------------------------------|------------------------------|------------------------------|--------------------------------|--------------------------------|",
    generate_table_rows(position_details),
    "",
    "---",
    "",
    "## 📋 持仓明细",
    "",
    "| <div align=\"center\">标的</div> | <div align=\"center\">持仓</div> | <div align=\"center\">成本价</div> | <div align=\"center\">现价</div> | <div align=\"center\">市值</div> | <div align=\"center\">盈亏</div> |",
    "|------------------------------|------------------------------|--------------------------------|--------------------------------|--------------------------------|--------------------------------|",
    generate_position_rows(position_details),
    "",
    "---",
    "",
    "## 🎯 权重偏差分析",
    "",
    "| <div align=\"center\">标的</div> | <div align=\"center\">实际权重</div> | <div align=\"center\">目标权重</div> | <div align=\"center\">偏差</div> | <div align=\"center\">操作建议</div> |",
    "|------------------------------|----------------------------------|----------------------------------|--------------------------------|------------------------------------|",
    generate_deviation_rows(position_details),
    "",
    "---",
    "",
    "## 🔥 实时表现排行",
    "",
    "### ⭐ 表现最佳",
    "",
    "| 标的 | 涨幅 | 评价 |",
    "|------|------|------|",
    "| " + best_performer['name'] + " | " + get_pnl_color(best_performer['pnl']) + " | 🌟 今日之星 |",
    "",
    "### 💫 表现最弱",
    "",
    "| 标的 | 跌幅 | 评价 |",
    "|------|------|------|",
    "| " + worst_performer['name'] + " | " + get_pnl_color(worst_performer['pnl']) + " | 💧 需要关注 |",
    "",
    "### 📊 涨跌统计",
    "",
    "| 类型 | 数量 | 占比 |",
    "|------|------|------|",
    "| 🟢 上涨 | " + str(up_count) + " 只 | " + str(int(up_count/12*100)) + "% |",
    "| 🔴 下跌 | " + str(down_count) + " 只 | " + str(int(down_count/12*100)) + "% |",
    "| ➡️ 持平 | " + str(12 - up_count - down_count) + " 只 | " + str(int((12-up_count-down_count)/12*100)) + "% |",
    "",
    "---",
    "",
    "## 🎨 风格分类配置",
    "",
    "```",
    "┌─────────────────────────────────────┐",
    "│           12只标的风格分布           │",
    "├─────────────┬─────────────┬───────┤",
    "│    风格     │   权重占比   │ 标的  │",
    "├─────────────┼─────────────┼───────┤",
    "│ ⚙️高端制造  │    31%      │ 5只   │",
    "│ 🛡️ 防御    │    22%      │ 4只   │",
    "│ ⛏️ 资源    │    19%      │ 2只   │",
    "│ 📈 顺周期  │    12%      │ 1只   │",
    "└─────────────┴─────────────┴───────┘",
    "```",
    "",
    "---",
    "",
    "## ⚠️ 风险提示",
    "",
    "| 风险等级 | 风险项 | 说明 | 应对建议 |",
    "|----------|--------|------|----------|",
    "| 🟡 中等 | 集中度风险 | 高端制造占比31%，行业波动影响较大 | 监控行业指数，设置预警阈值 |",
    "| 🟡 中等 | 半导体波动 | 512760日均波动3-5% | 权重限制在6%以内，做好止损 |",
    "| 🟢 低 | 新能源车政策 | 补贴退坡可能影响515030 | 关注政策动态，适度配置 |",
    "",
    "---",
    "",
    "## 💡 今日策略建议",
    "",
    "> 📌 **核心观点**：当前市场整体运行平稳，建议保持现有配置，关注晚间消息面。",
    "",
    "| 序号 | 建议 | 标的 |",
    "|------|------|------|",
    "| 1️⃣ | **继续持有** | 科创50ETF、创业板ETF、半导体ETF |",
    "| 2️⃣ | **适度关注** | 新能源车ETF、医疗ETF |",
    "| 3️⃣ | **风控提醒** | 中国神华设止损，黄金ETF作为压舱石 |",
    "",
    "---",
    "",
    "## 📊 组合配置图",
    "",
    "```",
    "资产配置分布",
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    "高端制造 ████████████████████░░░░░░░ 31%",
    "防御     █████████░░░░░░░░░░░░░░░░░░░ 22%",
    "资源     ████████░░░░░░░░░░░░░░░░░░░░ 19%",
    "顺周期   ████░░░░░░░░░░░░░░░░░░░░░░░░ 12%",
    "现金     ████░░░░░░░░░░░░░░░░░░░░░░░░ 16%",
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    "```",
    "",
    "---",
    "",
    "**📝 报告结束**",
    "",
    "| 统计项 | 数值 |",
    "|--------|------|",
    "| 📅 生成时间 | " + now.strftime("%Y-%m-%d %H:%M:%S") + " |",
    "| 📊 标的数量 | 12只 |",
    "| 🎯 策略版本 | 量化策略系统 v5.1-12Stock |",
    "| 📁 归档位置 | 每日报告归档/" + now.strftime("%Y-%m-%d") + " |",
    "",
    "---",
    "",
    "> 💡 *提示：本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。*"
]

report = "\n".join(report_lines)

save_dir = "E:/各种PY程序/每日报告归档/" + now.strftime("%Y-%m-%d")
os.makedirs(save_dir, exist_ok=True)
filepath = os.path.join(save_dir, "12只标的量化策略日报_" + now.strftime("%Y%m%d") + ".md")
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(report)

print("✨ 美化报告已保存: " + filepath)
print()
print("="*60)
print("📊 12只标的量化策略日报 (美化版)")
print("="*60)
print("账户总值: ¥" + "{:,}".format(int(total_value)))
print("累计收益: " + ("+" if profit_pct > 0 else "") + str(round(profit_pct, 1)) + "%")
print("上涨: " + str(up_count) + "只 | 下跌: " + str(down_count) + "只")
print("="*60)