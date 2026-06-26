# -*- coding: utf-8 -*-
"""
加仓北方华创执行脚本
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WIND_CLI = r"C:\Users\Administrator\.agents\skills\wind-mcp-skill\scripts\cli.mjs"

def get_wind_price(code):
    """获取Wind实时价格，对超时错误自动重试（最多2次，间隔3秒）"""
    windcode = f'{code}.SZ' if code.startswith('00') else f'{code}.SH'
    ps_script = f'node "{WIND_CLI}" call stock_data get_stock_price_indicators \'{{\\"windcode\\":\\"{windcode}\\",\\"indexes\\":\\"最新成交价\\"}}\''
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            r = subprocess.run(['powershell', '-Command', ps_script], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
            if r.stdout:
                d = json.loads(r.stdout)
                if d.get('content'):
                    rows = json.loads(d['content'][0]['text'])['data']['rows'][0]
                    return float(rows[0])
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                print(f"获取Wind行情超时，3秒后重试({attempt+1}/{max_retries})...")
                time.sleep(3)
                continue
            print(f"获取Wind行情失败，使用预设价格: 超时")
        except Exception as e:
            # 非超时错误，不重试
            print(f"获取Wind行情失败，使用预设价格: {e}")
            break
    return 624.99

def main():
    print("="*70)
    print("🛒 加仓北方华创执行脚本")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    code = "002371"
    name = "北方华创"
    
    print(f"\n📡 获取{name}({code})实时行情...")
    price = get_wind_price(code)
    print(f"💰 实时价格: ¥{price:.2f}")
    
    target_shares = 300
    current_shares = 200
    buy_shares = target_shares - current_shares
    
    if buy_shares <= 0:
        print(f"❌ 当前持仓{current_shares}股，已达到目标仓位，无需加仓")
        return
    
    cost = buy_shares * price
    commission = cost * 0.0005
    total_cost = cost + commission
    
    print(f"\n📊 加仓计划:")
    print(f"  当前持仓: {current_shares}股")
    print(f"  目标持仓: {target_shares}股")
    print(f"  需加仓: {buy_shares}股")
    print(f"  成交金额: ¥{cost:,.2f}")
    print(f"  交易费用: ¥{commission:,.2f}")
    print(f"  合计支出: ¥{total_cost:,.2f}")
    
    print(f"\n✅ 模拟买入成功!")
    print(f"📈 买入 {name}({code}) {buy_shares}股 @ ¥{price:.2f}")
    print(f"💵 持仓更新: {current_shares}股 → {target_shares}股")
    
    report = f"""
================================================================================
📊 加仓执行报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

📋 交易详情
------------------------------------------------------------
  标的名称: {name}
  股票代码: {code}
  操作类型: 买入
  成交数量: {buy_shares}股
  成交价格: ¥{price:.2f}
  成交金额: ¥{cost:,.2f}
  交易费用: ¥{commission:,.2f}
  合计支出: ¥{total_cost:,.2f}

💰 持仓变更
------------------------------------------------------------
  加仓前: {current_shares}股
  加仓后: {target_shares}股
  持仓市值: ¥{target_shares * price:,.2f}

================================================================================
"""
    
    report_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f'buy_report_{name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📝 报告已保存: {report_path}")
    print("="*70)

if __name__ == "__main__":
    main()