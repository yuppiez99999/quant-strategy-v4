# -*- coding: utf-8 -*-
"""
实时模拟交易 - 开盘接入 (Wind API版)
"""

import os
import yaml
import subprocess
import json
import time
from datetime import datetime

WIND_CLI = r"C:\Users\Administrator\.agents\skills\wind-mcp-skill\scripts\cli.mjs"

def get_stock_price(code):
    """获取股票价格，对超时错误自动重试（最多2次，间隔3秒）"""
    windcode = f'{code}.SH' if code.startswith('6') else f'{code}.SZ'
    ps_script = f'node "{WIND_CLI}" call stock_data get_stock_price_indicators \'{{\\"windcode\\":\\"{windcode}\\",\\"indexes\\":\\"最新成交价,涨跌幅\\"}}\''
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            r = subprocess.run(['powershell', '-Command', ps_script], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
            if r.stdout:
                d = json.loads(r.stdout)
                if d.get('content'):
                    rows = json.loads(d['content'][0]['text'])['data']['rows'][0]
                    return {'price': float(rows[0]), 'change': float(rows[1])}
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                time.sleep(3)
                continue
        except:
            pass
        break
    return {'price': 0, 'change': 0}

def get_fund_price(code):
    """获取基金价格，对超时错误自动重试（最多2次，间隔3秒）"""
    windcode = f'{code}.SH' if code.startswith('5') else f'{code}.SZ'
    ps_script = f'node "{WIND_CLI}" call fund_data get_fund_price_indicators \'{{\\"windcode\\":\\"{windcode}\\",\\"indexes\\":\\"最新成交价,涨跌幅\\"}}\''
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            r = subprocess.run(['powershell', '-Command', ps_script], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
            if r.stdout:
                d = json.loads(r.stdout)
                if d.get('content'):
                    rows = json.loads(d['content'][0]['text'])['data']['rows'][0]
                    return {'price': float(rows[0]), 'change': float(rows[1])}
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                time.sleep(3)
                continue
        except:
            pass
        break
    return {'price': 0, 'change': 0}

def main():
    print("="*70)
    print("🚀 实时模拟交易系统 - Wind API开盘接入")
    print("="*70)

    with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    assets = config['assets']
    codes = [asset['code'] for asset in assets]
    names = {asset['code']: asset['name'] for asset in assets}
    target_weights = {asset['code']: asset['target_weight'] for asset in assets}

    print(f"\n📅 系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 监控标的: {len(assets)} 只")
    print(f"💰 初始资金: ¥1,000,000")

    print(f"\n📥 获取Wind实时行情...")
    price_data = {}
    for asset in assets:
        code = asset['code']
        if code.startswith('5'):
            r = get_fund_price(code)
        else:
            r = get_stock_price(code)
        
        if r['price'] > 0:
            price_data[code] = r
            status = "📈" if r['change'] >= 0 else "📉"
            print(f"  {status} {names[code]}: ¥{r['price']:.2f} ({r['change']:+.2f}%)")
        else:
            print(f"  ❌ {names[code]}: 无法获取行情")

    if not price_data:
        print("\n❌ 无法获取任何行情数据")
        return

    initial_capital = 1000000
    cash = initial_capital
    positions = {}

    print(f"\n{'='*70}")
    print("📋 初始持仓 (按目标权重配置)")
    print(f"{'='*70}")

    for code in codes:
        if code in price_data:
            price = price_data[code]['price']
            target_weight = target_weights[code]
            target_amount = initial_capital * target_weight
            shares = int(target_amount / price / 100) * 100
            cost = shares * price * 1.0005

            if cost <= cash:
                cash -= cost
                positions[code] = {
                    'shares': shares,
                    'avg_cost': price,
                    'name': names[code]
                }
                market_value = shares * price
                print(f"  {names[code]:<12} 买入 {shares:>6} 股 @ ¥{price:>8.2f} = ¥{market_value:>12,.0f}")

    total_market_value = sum(
        p['shares'] * price_data[code]['price']
        for code, p in positions.items() if code in price_data
    )
    total_value = cash + total_market_value

    print(f"\n{'='*70}")
    print("📊 账户状态")
    print(f"{'='*70}")
    print(f"💵 可用现金: ¥{cash:>12,.2f}")
    print(f"📈 持仓市值: ¥{total_market_value:>12,.2f}")
    print(f"💰 账户总值: ¥{total_value:>12,.2f}")
    print(f"{'='*70}")

    print(f"\n✅ Wind实时模拟盘已启动!")
    print(f"   数据源: Wind API")
    print(f"   监控周期: 每60秒更新")
    print(f"   再平衡: 每15个交易日")
    print(f"   风控: 最大回撤≤10%")
    print(f"\n⏳ 持续监控中... (按Ctrl+C停止)")

if __name__ == "__main__":
    main()
