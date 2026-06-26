# -*- coding: utf-8 -*-
"""
快速测试脚本 - 12只标的量化策略
"""

import os
import sys
import yaml
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def main():
    print("="*70)
    print("12只标的量化策略 - 快速测试")
    print("="*70)
    
    with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    assets = config['assets']
    codes = [asset['code'] for asset in assets]
    names = {asset['code']: asset['name'] for asset in assets}
    target_weights = {asset['code']: asset['target_weight'] for asset in assets}
    
    print(f"\n📊 标的配置:")
    print(f"{'名称':<12} {'代码':<10} {'权重':<8}")
    print("-"*70)
    for asset in assets:
        print(f"{asset['name']:<12} {asset['code']:<10} {asset['target_weight']*100:>5.1f}%")
    print("-"*70)
    print(f"{'合计':<22} {sum([a['target_weight'] for a in assets])*100:>5.1f}%")
    
    print(f"\n📥 加载数据...")
    price_data = {}
    dates = None
    
    for asset in assets:
        code = asset['code']
        filepath = os.path.join('data/cache', f'kline_{code}_daily.parquet')
        if os.path.exists(filepath):
            df = pd.read_parquet(filepath)
            price_data[code] = df
            print(f"  ✅ {names[code]} ({code}): {len(df)} 条数据")
            if dates is None:
                dates = df.index.tolist()
            else:
                common_dates = set(dates) & set(df.index.tolist())
                dates = sorted(list(common_dates))
    
    if not dates:
        print("❌ 没有可用数据")
        return
    
    print(f"\n📅 日期范围: {dates[0].date()} - {dates[-1].date()}")
    print(f"   交易日数: {len(dates)}")
    
    initial_capital = 1000000
    cash = initial_capital
    positions = {}
    equity_curve = []
    peak_value = initial_capital
    max_drawdown = 0
    
    print(f"\n🚀 开始回测...")
    last_rebalance = None
    
    for i, date in enumerate(dates):
        prices = {}
        for code in codes:
            if code in price_data and date in price_data[code].index:
                prices[code] = float(price_data[code].loc[date, 'close'])
        
        if not prices:
            continue
        
        total = cash
        for code, pos in positions.items():
            if code in prices:
                total += pos['shares'] * prices[code]
        
        if total > peak_value:
            peak_value = total
        drawdown = (peak_value - total) / peak_value
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        
        equity_curve.append({
            'date': date,
            'value': total,
            'drawdown': drawdown
        })
        
        if last_rebalance is None or (date - last_rebalance).days >= 15:
            for code in codes:
                if code not in prices:
                    continue
                
                target_weight = target_weights[code]
                target_amount = total * target_weight
                
                current_shares = positions.get(code, {}).get('shares', 0)
                current_amount = current_shares * prices[code]
                
                diff_amount = target_amount - current_amount
                
                if abs(diff_amount) / total < 0.01:
                    continue
                
                price = prices[code]
                shares = int(abs(diff_amount) / price / 100) * 100
                
                if shares > 0:
                    commission = shares * price * 0.0005
                    
                    if diff_amount > 0:
                        cost = shares * price + commission
                        if cost > cash:
                            continue
                        cash -= cost
                        
                        if code not in positions:
                            positions[code] = {'shares': 0, 'avg_cost': 0}
                        
                        old_cost = positions[code]['shares'] * positions[code]['avg_cost']
                        positions[code]['shares'] += shares
                        positions[code]['avg_cost'] = (old_cost + shares * price) / positions[code]['shares']
                    else:
                        if code not in positions or positions[code]['shares'] < shares:
                            continue
                        
                        positions[code]['shares'] -= shares
                        if positions[code]['shares'] == 0:
                            del positions[code]
                        
                        cash += shares * price - commission
            
            last_rebalance = date
        
        if (i + 1) % 200 == 0:
            print(f"⏳ 已完成 {i + 1}/{len(dates)} 个交易日")
    
    print(f"\n✅ 回测完成!")
    
    values = [e['value'] for e in equity_curve]
    dates_list = [e['date'] for e in equity_curve]
    
    initial = values[0]
    final = values[-1]
    total_return = (final - initial) / initial
    
    years = (dates_list[-1] - dates_list[0]).days / 365
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    
    daily_rets = np.diff(values) / values[:-1]
    annual_vol = np.std(daily_rets) * np.sqrt(252) if len(daily_rets) > 0 else 0
    sharpe = (annual_return - 0.03) / annual_vol if annual_vol > 0 else 0
    
    print(f"\n{'='*70}")
    print("📊 回测结果")
    print(f"{'='*70}")
    print(f"💰 初始资金: ¥{initial:,.0f}")
    print(f"🎯 最终资金: ¥{final:,.0f}")
    print(f"📈 总收益率: {total_return*100:+.2f}%")
    print(f"📊 年化收益: {annual_return*100:+.2f}%")
    print(f"🎲 年化波动: {annual_vol*100:.2f}%")
    print(f"📉 最大回撤: {max_drawdown*100:.2f}%")
    print(f"⚖️ 夏普比率: {sharpe:.2f}")
    print(f"{'='*70}")
    
    print(f"\n🎯 目标达成情况:")
    print(f"   年化收益≥8%: {'✅' if annual_return >= 0.08 else '❌'} ({annual_return*100:.2f}%)")
    print(f"   最大回撤≤10%: {'✅' if max_drawdown <= 0.10 else '❌'} ({max_drawdown*100:.2f}%)")
    
    print(f"\n📋 最终持仓:")
    print(f"{'名称':<12} {'代码':<10} {'持仓':<8} {'市值':<14}")
    print(f"{'-'*70}")
    
    total_market_value = 0
    final_prices = {}
    for code in codes:
        if code in price_data and dates[-1] in price_data[code].index:
            final_prices[code] = float(price_data[code].loc[dates[-1], 'close'])
    
    for code in codes:
        if code in positions:
            shares = positions[code]['shares']
            price = final_prices.get(code, 0)
            market_value = shares * price
            total_market_value += market_value
            print(f"{names[code]:<12} {code:<10} {shares:<8} ¥{market_value:<14,.2f}")
    
    print(f"{'-'*70}")
    total_value = cash + total_market_value
    print(f"{'持仓市值':<22} ¥{total_market_value:<14,.2f}")
    print(f"{'可用现金':<22} ¥{cash:<14,.2f}")
    print(f"{'账户总值':<22} ¥{total_value:<14,.2f}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
