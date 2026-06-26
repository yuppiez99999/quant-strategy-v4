# -*- coding: utf-8 -*-
"""
执行方案A再平衡：更新positions.json为9标的组合
新增半导体ETF(512760) + 证券ETF(512880)
"""

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
POSITIONS_FILE = os.path.join(CONFIG_DIR, 'positions.json')

# 方案A目标权重
TARGET_WEIGHTS = {
    "601088": 0.12,  # 中国神华
    "600276": 0.10,  # 恒瑞医药
    "510300": 0.15,  # 沪深300ETF
    "512100": 0.10,  # 中证1000ETF
    "588000": 0.15,  # 科创50ETF
    "159915": 0.12,  # 创业板ETF
    "518880": 0.12,  # 华安黄金ETF
    "512760": 0.08,  # 半导体ETF国泰
    "512880": 0.07,  # 证券ETF国泰
}

# 当前价格
PRICES = {
    "601088": 48.15,
    "600276": 46.26,
    "510300": 4.777,
    "512100": 3.281,
    "588000": 1.754,
    "159915": 3.867,
    "518880": 8.674,
    "512760": 1.52,
    "512880": 1.28
}

# 标的名称
NAMES = {
    "601088": "中国神华",
    "600276": "恒瑞医药",
    "510300": "沪深300ETF",
    "512100": "中证1000ETF",
    "588000": "科创50ETF",
    "159915": "创业板ETF",
    "518880": "华安黄金ETF",
    "512760": "半导体ETF国泰",
    "512880": "证券ETF国泰"
}

def main():
    print("=== 执行方案A再平衡 ===")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 读取当前持仓
    with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_value = data.get('total_value', 2455713)
    
    print(f"\n账户总值: ¥{total_value:,.0f}")
    
    # 计算各标的目标持仓
    new_positions = {}
    summary = []
    
    for code, weight in TARGET_WEIGHTS.items():
        target_mv = total_value * weight
        price = PRICES.get(code, 0)
        if price > 0:
            shares = int(target_mv / price / 100) * 100
            avg_cost = data.get('positions', {}).get(code, {}).get('avg_cost', price)
            new_positions[code] = {
                "shares": shares,
                "avg_cost": avg_cost
            }
            
            current_shares = data.get('positions', {}).get(code, {}).get('shares', 0)
            diff = shares - current_shares
            action = "新增" if current_shares == 0 else ("买入" if diff > 0 else "卖出" if diff < 0 else "持有")
            abs_diff = abs(diff)
            
            summary.append({
                "code": code,
                "name": NAMES.get(code, code),
                "action": action,
                "shares": shares,
                "diff": diff,
                "abs_diff": abs_diff,
                "price": price,
                "amount": abs_diff * price,
                "weight": weight
            })
    
    # 更新数据
    data['positions'] = new_positions
    data['prices'] = PRICES
    data['last_update'] = datetime.now().isoformat()
    
    # 保存
    with open(POSITIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # 输出汇总
    print("\n" + "="*60)
    print("再平衡结果汇总")
    print("="*60)
    
    print("\n📊 目标权重配置:")
    for item in sorted(summary, key=lambda x: x['weight'], reverse=True):
        print(f"  {item['name']}: {item['weight']:.0%}")
    
    print("\n📋 交易明细:")
    sells = [s for s in summary if s['action'] == '卖出']
    buys = [s for s in summary if s['action'] == '买入']
    adds = [s for s in summary if s['action'] == '新增']
    holds = [s for s in summary if s['action'] == '持有']
    
    if sells:
        print("\n  💸 卖出:")
        for s in sells:
            print(f"    - {s['name']}: 卖出 {s['abs_diff']:,}份 @ ¥{s['price']:.2f} = ¥{s['amount']:,.0f}")
    
    if buys:
        print("\n  🛒 买入:")
        for s in buys:
            print(f"    - {s['name']}: 买入 {s['abs_diff']:,}份 @ ¥{s['price']:.2f} = ¥{s['amount']:,.0f}")
    
    if adds:
        print("\n  ➕ 新增:")
        for s in adds:
            print(f"    - {s['name']}: 买入 {s['shares']:,}份 @ ¥{s['price']:.2f} = ¥{s['shares'] * s['price']:,.0f}")
    
    if holds:
        print("\n  ✅ 持有:")
        for s in holds:
            print(f"    - {s['name']}: {s['shares']:,}份")
    
    print(f"\n✅ 配置已更新: {POSITIONS_FILE}")
    print("\n⚠️ 注意: 下午13:00开盘后，实时交易系统将自动同步此配置")

if __name__ == "__main__":
    main()
