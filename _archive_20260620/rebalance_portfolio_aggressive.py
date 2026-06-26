#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调仓脚本：从旧配置到激进组合
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import yaml

# 旧权重配置（上一次的配置）
OLD_WEIGHTS = {
    "601088": 0.20,
    "600995": 0.00,
    "600989": 0.0359,
    "600875": 0.1617,
    "600406": 0.00,
    "300274": 0.1115,
    "000425": 0.00,
    "002371": 0.0576,
    "600276": 0.0187,
    "600089": 0.0147,
    "688017": 0.20,
    "518880": 0.20
}

# 激进组合配置
NEW_WEIGHTS = {
    "601088": 0.1667,
    "600995": 0.00,
    "600989": 0.1667,
    "600875": 0.1667,
    "600406": 0.00,
    "300274": 0.1667,
    "000425": 0.00,
    "002371": 0.1667,
    "600276": 0.00,
    "600089": 0.00,
    "688017": 0.1667,
    "518880": 0.00
}

NAMES = {
    "601088": "中国神华",
    "600995": "南网储能",
    "600989": "宝丰能源",
    "600875": "东方电气",
    "600406": "国电南瑞",
    "300274": "阳光电源",
    "000425": "徐工机械",
    "002371": "北方华创",
    "600276": "恒瑞医药",
    "600089": "特变电工",
    "688017": "绿的谐波",
    "518880": "华安黄金ETF"
}

PRICES = {
    "601088": 44.80,
    "600995": 14.19,
    "600989": 25.15,
    "600875": 35.69,
    "600406": 25.48,
    "300274": 178.99,
    "000425": 9.61,
    "002371": 670.25,
    "600276": 49.20,
    "600089": 26.03,
    "688017": 338.47,
    "518880": 9.45
}

TOTAL_CAPITAL = 1000000

def main():
    print("=" * 80)
    print("📊 激进组合调仓分析")
    print("=" * 80)
    
    # 1. 旧持仓配置
    print("\n📋 1. 旧持仓配置")
    print("-" * 70)
    print(f"{'标的':<12} {'代码':<10} {'旧权重':>8} {'目标市值':>12} {'股数':>8}")
    print("-" * 70)
    
    old_positions = {}
    for code in OLD_WEIGHTS:
        old_w = OLD_WEIGHTS[code]
        if old_w > 0:
            target_mv = TOTAL_CAPITAL * old_w
            shares = int(target_mv / PRICES[code] / 100) * 100
            old_positions[code] = shares
            print(f"{NAMES[code]:<12} {code:<10} {old_w*100:>7.1f}%  ¥{target_mv:>10,.0f}  {shares:>8}")
        else:
            print(f"{NAMES[code]:<12} {code:<10} {'-':>7}  {'-':>10}  {'-':>8}")
    
    print("-" * 70)
    
    # 2. 新持仓配置（激进组合）
    print("\n📋 2. 激进组合配置")
    print("-" * 70)
    print(f"{'标的':<12} {'代码':<10} {'新权重':>8} {'目标市值':>12} {'股数':>8}")
    print("-" * 70)
    
    new_positions = {}
    for code in NEW_WEIGHTS:
        new_w = NEW_WEIGHTS[code]
        if new_w > 0:
            target_mv = TOTAL_CAPITAL * new_w
            shares = int(target_mv / PRICES[code] / 100) * 100
            new_positions[code] = shares
            print(f"{NAMES[code]:<12} {code:<10} {new_w*100:>7.1f}%  ¥{target_mv:>10,.0f}  {shares:>8}")
        else:
            print(f"{NAMES[code]:<12} {code:<10} {'-':>7}  {'-':>10}  {'-':>8}")
    
    print("-" * 70)
    
    # 3. 调仓订单
    print("\n📝 3. 调仓订单")
    print("-" * 70)
    print(f"{'操作':<6} {'标的':<12} {'代码':<10} {'股数':>8} {'价格':>10} {'金额':>12}")
    print("-" * 70)
    
    sell_orders = []
    buy_orders = []
    
    # 检查所有标的
    for code in OLD_WEIGHTS:
        old_shares = old_positions.get(code, 0)
        new_shares = new_positions.get(code, 0)
        
        if old_shares > new_shares:
            # 需要卖出
            sell_shares = old_shares - new_shares
            sell_amount = sell_shares * PRICES[code]
            sell_orders.append({
                'code': code,
                'name': NAMES[code],
                'shares': sell_shares,
                'price': PRICES[code],
                'amount': sell_amount
            })
        elif new_shares > old_shares:
            # 需要买入
            buy_shares = new_shares - old_shares
            buy_amount = buy_shares * PRICES[code]
            buy_orders.append({
                'code': code,
                'name': NAMES[code],
                'shares': buy_shares,
                'price': PRICES[code],
                'amount': buy_amount
            })
    
    # 打印卖出订单
    for order in sell_orders:
        print(f"🔴 SELL  {order['name']:<12} {order['code']:<10} {order['shares']:>8}  ¥{order['price']:>9.2f}  ¥{order['amount']:>11,.0f}")
    
    # 打印买入订单
    for order in buy_orders:
        print(f"🟢 BUY   {order['name']:<12} {order['code']:<10} {order['shares']:>8}  ¥{order['price']:>9.2f}  ¥{order['amount']:>11,.0f}")
    
    print("-" * 70)
    
    # 统计
    total_sell = sum(o['amount'] for o in sell_orders)
    total_buy = sum(o['amount'] for o in buy_orders)
    
    print(f"\n📊 调仓统计：")
    print(f"  卖出总额：¥{total_sell:,.0f}")
    print(f"  买入总额：¥{total_buy:,.0f}")
    print(f"  净现金变动：¥{total_sell - total_buy:,.0f}")
    
    # 4. 详细分析
    print("\n" + "=" * 80)
    print("📈 4. 详细调仓分析")
    print("=" * 80)
    
    print(f"\n🔴 需清仓标的（新权重=0）：")
    for code in OLD_WEIGHTS:
        if OLD_WEIGHTS[code] > 0 and NEW_WEIGHTS[code] == 0:
            shares = old_positions.get(code, 0)
            amount = shares * PRICES[code]
            if shares > 0:
                print(f"  • {NAMES[code]} ({code})：卖出 {shares}股，约 ¥{amount:,.0f}")
    
    print(f"\n🟢 需大幅增持标的：")
    for code in NEW_WEIGHTS:
        if NEW_WEIGHTS[code] > OLD_WEIGHTS[code]:
            diff_w = NEW_WEIGHTS[code] - OLD_WEIGHTS[code]
            diff_amount = TOTAL_CAPITAL * diff_w
            if diff_w >= 0.10:
                print(f"  • {NAMES[code]} ({code})：+{diff_w*100:.1f}%，约 ¥{diff_amount:,.0f}")
            elif diff_w > 0:
                print(f"  • {NAMES[code]} ({code})：+{diff_w*100:.1f}%，约 ¥{diff_amount:,.0f}")
    
    print(f"\n🟡 需小幅减仓标的：")
    for code in NEW_WEIGHTS:
        if NEW_WEIGHTS[code] < OLD_WEIGHTS[code] and NEW_WEIGHTS[code] > 0:
            diff_w = OLD_WEIGHTS[code] - NEW_WEIGHTS[code]
            diff_amount = TOTAL_CAPITAL * diff_w
            print(f"  • {NAMES[code]} ({code})：-{diff_w*100:.1f}%，约 ¥{diff_amount:,.0f}")
    
    print("\n" + "=" * 80)
    print("✅ 激进组合调仓分析完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
