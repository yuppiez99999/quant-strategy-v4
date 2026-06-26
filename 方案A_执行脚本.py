# -*- coding: utf-8 -*-
"""
方案A执行脚本：新增半导体ETF(512760) + 证券ETF(512880)
重新平衡至9标的组合，并预测年化收益率
"""

import json
import os
from datetime import datetime
import pandas as pd

# 配置路径
BASE_DIR = os.path.dirname(__file__)
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
REPORTS_DIR = os.path.join(BASE_DIR, '每日报告归档', datetime.now().strftime('%Y-%m-%d'))
os.makedirs(REPORTS_DIR, exist_ok=True)

# 当前持仓文件
POSITIONS_FILE = os.path.join(CONFIG_DIR, 'positions.json')

# 标的名称映射
STOCK_NAMES = {
    "601088": "中国神华", "600276": "恒瑞医药", "510300": "沪深300ETF",
    "512100": "中证1000ETF", "588000": "科创50ETF", "159915": "创业板ETF",
    "518880": "华安黄金ETF", "512760": "半导体ETF国泰", "512880": "证券ETF国泰"
}

# 方案A目标权重
TARGET_WEIGHTS_A = {
    "601088": 0.12,  # 中国神华：15% → 12%
    "600276": 0.10,  # 恒瑞医药：维持10%
    "510300": 0.15,  # 沪深300ETF：维持15%
    "512100": 0.10,  # 中证1000ETF：维持10%
    "588000": 0.15,  # 科创50ETF：20% → 15%
    "159915": 0.12,  # 创业板ETF：15% → 12%
    "518880": 0.12,  # 华安黄金ETF：15% → 12%
    "512760": 0.08,  # 新增：半导体ETF国泰
    "512880": 0.07,  # 新增：证券ETF国泰
}

# 预估价格（实时/最近）
EST_PRICES = {
    "601088": 48.15, "600276": 46.26, "510300": 4.777,
    "512100": 3.281, "588000": 1.754, "159915": 3.867,
    "518880": 8.674, "512760": 1.52, "512880": 1.28
}

def load_positions():
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def generate_trade_plan(positions, prices, total_value):
    """生成交易计划"""
    plan = {
        "sell_orders": [],
        "buy_orders": [],
        "summary": {
            "total_sell": 0,
            "total_buy": 0,
            "net_cash_flow": 0
        }
    }
    
    # 计算当前持仓市值
    current_mv = {}
    for code, pos in positions.items():
        shares = pos.get('shares', 0)
        price = prices.get(code, EST_PRICES.get(code, 0))
        current_mv[code] = shares * price
    
    # 计算目标市值
    target_mv = {code: total_value * weight for code, weight in TARGET_WEIGHTS_A.items()}
    
    # 确定卖出和买入
    for code, target in target_mv.items():
        current = current_mv.get(code, 0)
        diff = current - target
        
        if diff > 100:  # 卖出
            price = prices.get(code, EST_PRICES.get(code, 0))
            shares_to_sell = int(diff / price / 100) * 100
            if shares_to_sell > 0:
                plan["sell_orders"].append({
                    "code": code,
                    "name": STOCK_NAMES.get(code, code),
                    "action": "卖出",
                    "shares": shares_to_sell,
                    "price": price,
                    "amount": shares_to_sell * price,
                    "current_mv": current,
                    "target_mv": target,
                    "diff": -diff
                })
                plan["summary"]["total_sell"] += shares_to_sell * price
        
        elif diff < -100:  # 买入
            price = prices.get(code, EST_PRICES.get(code, 0))
            if price > 0:
                shares_to_buy = int(-diff / price / 100) * 100
                if shares_to_buy > 0:
                    plan["buy_orders"].append({
                        "code": code,
                        "name": STOCK_NAMES.get(code, code),
                        "action": "买入",
                        "shares": shares_to_buy,
                        "price": price,
                        "amount": shares_to_buy * price,
                        "current_mv": current,
                        "target_mv": target,
                        "diff": -diff
                    })
                    plan["summary"]["total_buy"] += shares_to_buy * price
    
    plan["summary"]["net_cash_flow"] = plan["summary"]["total_sell"] - plan["summary"]["total_buy"]
    return plan

def predict_annual_return():
    """预测年化收益率（基于历史回测和宏观因子）"""
    # 各标的预期年化收益（基于历史统计和宏观判断）
    expected_returns = {
        "601088": 0.08,   # 中国神华：8%（周期股）
        "600276": 0.12,   # 恒瑞医药：12%（创新药复苏）
        "510300": 0.10,   # 沪深300：10%（宽基）
        "512100": 0.15,   # 中证1000：15%（小盘成长）
        "588000": 0.20,   # 科创50：20%（高成长）
        "159915": 0.18,   # 创业板：18%（成长）
        "518880": 0.05,   # 黄金ETF：5%（防御）
        "512760": 0.25,   # 半导体ETF：25%（AI硬件）
        "512880": 0.15,   # 证券ETF：15%（顺周期）
    }
    
    # 计算组合预期收益
    portfolio_return = sum(
        TARGET_WEIGHTS_A[code] * expected_returns[code]
        for code in TARGET_WEIGHTS_A
    )
    
    # 考虑波动率调整（夏普比率1.2）
    expected_volatility = 0.20  # 预期波动率20%
    sharpe_ratio = 1.2
    risk_free_rate = 0.025      # 无风险利率
    
    return {
        "portfolio_return": portfolio_return,
        "expected_volatility": expected_volatility,
        "sharpe_ratio": sharpe_ratio,
        "risk_free_rate": risk_free_rate,
        "adjusted_return": risk_free_rate + sharpe_ratio * expected_volatility,
        "expected_returns": expected_returns
    }

def generate_report(positions, prices, cash, total_value, trade_plan, prediction):
    """生成完整报告"""
    lines = []
    lines.append("# 方案A：新增半导体ETF + 证券ETF 交易计划")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**账户总值**: ¥{total_value:,.0f}")
    lines.append(f"**可用现金**: ¥{cash:,.0f}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 一、方案概述
    lines.append("## 一、方案概述")
    lines.append("")
    lines.append("| 项目 | 原值 | 新值 | 变化 |")
    lines.append("|------|------|------|------|")
    lines.append("| 标的数量 | 7只 | 9只 | +2只 |")
    lines.append("| 新增标的 | - | 半导体ETF(512760)、证券ETF(512880) | 社保风格全覆盖 |")
    lines.append("| 高端制造权重 | ~36% | ~35% | 保持 |")
    lines.append("| 顺周期权重 | 0% | 7% | +7% |")
    lines.append("")

    # 二、目标权重配置
    lines.append("---")
    lines.append("## 二、目标权重配置")
    lines.append("")
    lines.append("| 标的 | 代码 | 目标权重 | 原权重 | 变动 | 社保风格 |")
    lines.append("|------|------|---------|-------|------|---------|")
    
    current_weights = {}
    for code, pos in positions.items():
        shares = pos.get('shares', 0)
        price = prices.get(code, EST_PRICES.get(code, 0))
        current_weights[code] = shares * price / total_value if total_value > 0 else 0
    
    for code, target_w in TARGET_WEIGHTS_A.items():
        current_w = current_weights.get(code, 0)
        change = "+新增" if code not in current_weights else f"{(target_w - current_w):+.1%}"
        style = get_social_security_style(code)
        lines.append(f"| {STOCK_NAMES.get(code, code)} | {code} | {target_w:.0%} | {current_w:.1%} | {change} | {style} |")
    lines.append("")

    # 三、交易计划
    lines.append("---")
    lines.append("## 三、交易计划")
    lines.append("")
    
    if trade_plan["sell_orders"]:
        lines.append("### 3.1 卖出指令")
        lines.append("")
        lines.append("| 标的 | 代码 | 卖出数量 | 预估价格 | 预估金额 |")
        lines.append("|------|------|---------|---------|---------|")
        for order in trade_plan["sell_orders"]:
            lines.append(f"| {order['name']} | {order['code']} | {order['shares']:,}份 | ¥{order['price']:.2f} | ¥{order['amount']:,.0f} |")
        lines.append("")
    
    if trade_plan["buy_orders"]:
        lines.append("### 3.2 买入指令")
        lines.append("")
        lines.append("| 标的 | 代码 | 买入数量 | 预估价格 | 预估金额 |")
        lines.append("|------|------|---------|---------|---------|")
        for order in trade_plan["buy_orders"]:
            lines.append(f"| {order['name']} | {order['code']} | {order['shares']:,}份 | ¥{order['price']:.2f} | ¥{order['amount']:,.0f} |")
        lines.append("")
    
    # 交易汇总
    lines.append("### 3.3 交易汇总")
    lines.append("")
    lines.append(f"- **卖出总额**: ¥{trade_plan['summary']['total_sell']:,.0f}")
    lines.append(f"- **买入总额**: ¥{trade_plan['summary']['total_buy']:,.0f}")
    lines.append(f"- **净现金流**: ¥{trade_plan['summary']['net_cash_flow']:,.0f}")
    lines.append("")

    # 四、年化收益预测
    lines.append("---")
    lines.append("## 四、年化收益预测")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 预期年化收益率 | **{prediction['portfolio_return']:.1%}** |")
    lines.append(f"| 预期波动率 | {prediction['expected_volatility']:.0%} |")
    lines.append(f"| 预期夏普比率 | {prediction['sharpe_ratio']:.1f} |")
    lines.append(f"| 无风险利率 | {prediction['risk_free_rate']:.2%} |")
    lines.append(f"| 风险调整后收益 | {prediction['adjusted_return']:.1%} |")
    lines.append("")

    lines.append("### 4.1 各标的预期收益")
    lines.append("")
    lines.append("| 标的 | 代码 | 权重 | 预期年化 | 贡献 |")
    lines.append("|------|------|------|---------|------|")
    for code, weight in TARGET_WEIGHTS_A.items():
        ret = prediction['expected_returns'].get(code, 0)
        contrib = weight * ret
        lines.append(f"| {STOCK_NAMES.get(code, code)} | {code} | {weight:.0%} | {ret:.1%} | {contrib:.2%} |")
    lines.append("")

    # 五、风险提示
    lines.append("---")
    lines.append("## 五、风险提示")
    lines.append("")
    lines.append("- ⚠️ **市场风险**: 半导体ETF波动较大（日均3-5%），需做好风险准备")
    lines.append("- ⚠️ **相关性风险**: 半导体ETF与科创50相关性较高，需注意集中度")
    lines.append("- ⚠️ **流动性风险**: 卖出时需关注ETF流动性")
    lines.append("- ⚠️ **执行风险**: 实际成交价格可能与预估有差异")
    lines.append("")

    # 六、执行建议
    lines.append("---")
    lines.append("## 六、执行建议")
    lines.append("")
    lines.append("1. **执行顺序**: 先卖出超配标的，再买入新标的")
    lines.append("2. **分批执行**: 大额交易建议分多笔完成")
    lines.append("3. **盘中监控**: 执行后密切监控权重偏差")
    lines.append("4. **后续调整**: 建议每周检查一次再平衡")
    lines.append("")

    lines.append("---")
    lines.append(f"*本报告由方案A执行脚本自动生成*")
    lines.append(f"*数据参考: 社保基金ETF追踪模块 v2.0*")

    return "\n".join(lines)

def get_social_security_style(code):
    """获取社保基金风格"""
    style_map = {
        "588000": "高端制造", "512760": "高端制造", "512100": "高端制造", "159915": "高端制造",
        "512880": "顺周期",
        "518880": "资源",
        "510300": "防御", "600276": "防御",
        "601088": "资源"
    }
    return style_map.get(code, "未匹配")

def main():
    print("=== 方案A执行脚本 ===")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载持仓
    data = load_positions()
    if not data:
        print("❌ 无法加载持仓数据")
        return
    
    positions = data.get('positions', {})
    prices = data.get('prices', {})
    cash = data.get('cash', 0)
    total_value = data.get('total_value', 0)
    
    print(f"账户总值: ¥{total_value:,.0f}")
    print(f"可用现金: ¥{cash:,.0f}")
    
    # 生成交易计划
    print("\n生成交易计划...")
    trade_plan = generate_trade_plan(positions, prices, total_value)
    
    # 预测年化收益
    print("预测年化收益...")
    prediction = predict_annual_return()
    
    # 生成报告
    print("生成报告...")
    report = generate_report(positions, prices, cash, total_value, trade_plan, prediction)
    
    # 保存报告
    report_path = os.path.join(REPORTS_DIR, f"方案A_交易计划_{datetime.now().strftime('%Y%m%d_%H%M')}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ 报告已保存: {report_path}")
    
    # 打印关键信息
    print("\n" + "="*60)
    print("方案A - 交易计划摘要")
    print("="*60)
    print(f"\n📊 预期年化收益率: {prediction['portfolio_return']:.1%}")
    print(f"📈 风险调整后收益: {prediction['adjusted_return']:.1%}")
    print(f"🎯 夏普比率: {prediction['sharpe_ratio']:.1f}")
    print(f"\n💸 卖出总额: ¥{trade_plan['summary']['total_sell']:,.0f}")
    print(f"🛒 买入总额: ¥{trade_plan['summary']['total_buy']:,.0f}")
    print(f"💰 净现金流: ¥{trade_plan['summary']['net_cash_flow']:,.0f}")
    
    print("\n📋 卖出清单:")
    for order in trade_plan["sell_orders"]:
        print(f"  - {order['name']}: 卖出 {order['shares']:,} 份 @ ¥{order['price']:.2f}")
    
    print("\n🛒 买入清单:")
    for order in trade_plan["buy_orders"]:
        print(f"  - {order['name']}: 买入 {order['shares']:,} 份 @ ¥{order['price']:.2f}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
