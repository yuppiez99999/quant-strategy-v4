#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import yaml

class PortfolioConfig:
    def __init__(self):
        self.codes = []
        self.names = {}
        self.target_weights = {}
        self.risk_weights = {}
        self.commission = {}
        self.min_hold_days = {}
        self.load_config()
    
    def load_config(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        for asset in config['assets']:
            code = asset['code']
            self.codes.append(code)
            self.names[code] = asset['name']
            self.target_weights[code] = asset['target_weight']
            self.risk_weights[code] = asset.get('risk_weight', 0.5)
            self.commission[code] = asset.get('commission', 0.0005)
            self.min_hold_days[code] = asset.get('min_hold_days', 5)

class TradingAccount:
    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.trade_log = []
    
    def buy(self, code, price, shares, commission_rate=0.0005):
        cost = shares * price
        commission = cost * commission_rate
        total_cost = cost + commission
        
        if total_cost > self.cash:
            return False, f"资金不足: 需要¥{total_cost:,.2f}, 可用¥{self.cash:,.2f}"
        
        self.cash -= total_cost
        
        if code not in self.positions:
            self.positions[code] = {'shares': 0, 'avg_cost': 0}
        
        old_shares = self.positions[code]['shares']
        old_cost = old_shares * self.positions[code]['avg_cost']
        new_shares = old_shares + shares
        new_cost = old_cost + cost
        
        self.positions[code]['shares'] = new_shares
        self.positions[code]['avg_cost'] = new_cost / new_shares if new_shares > 0 else 0
        
        self.trade_log.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': 'BUY',
            'code': code,
            'shares': shares,
            'price': price,
            'commission': commission
        })
        
        return True, f"买入成功"
    
    def get_total_value(self, prices):
        total = self.cash
        for code, pos in self.positions.items():
            if code in prices:
                total += pos['shares'] * prices[code]
        return total
    
    def save_positions(self):
        import json
        data = {
            'cash': self.cash,
            'positions': self.positions,
            'trade_log': self.trade_log,
            'saved_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open('data/positions.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n📁 持仓已保存到 data/positions.json")

def get_real_time_prices(codes):
    prices = {
        '601088': 44.80,
        '600995': 14.19,
        '600989': 25.15,
        '600875': 35.69,
        '600406': 25.48,
        '300274': 178.99,
        '000425': 9.61,
        '002371': 670.25,
        '600276': 49.20,
        '600089': 26.03,
        '688017': 338.47,
        '518880': 9.45
    }
    changes = {code: 0 for code in codes}
    return prices, changes

def load_settings(settings_path='config/settings.yaml'):
    with open(settings_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    print("📈 激进组合初始建仓")
    print("=" * 70)
    
    settings = load_settings()
    portfolio = PortfolioConfig()
    
    # 获取实时行情
    prices, _ = get_real_time_prices(portfolio.codes)
    
    # 创建账户并初始建仓
    account = TradingAccount(settings['capital']['total'])
    total_value = account.initial_capital
    
    print(f"\n💰 初始资金: ¥{total_value:,}")
    print(f"📅 建仓时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "-" * 70)
    
    # 按激进组合权重建仓
    for code in portfolio.codes:
        if code not in prices or prices[code] <= 0:
            continue
        
        target_weight = portfolio.target_weights.get(code, 0)
        if target_weight > 0:
            target_mv = total_value * target_weight
            buy_shares = int(target_mv / prices[code] / 100) * 100
            
            if buy_shares > 0:
                success, msg = account.buy(code, prices[code], buy_shares, portfolio.commission.get(code, 0.0005))
                if success:
                    print(f"🟢 买入 {portfolio.names[code]:<10} {code}: {buy_shares}股 @ ¥{prices[code]:.2f} = ¥{buy_shares * prices[code]:,.2f}")
                else:
                    print(f"🔴 买入 {portfolio.names[code]:<10} {code} 失败: {msg}")
    
    # 保存持仓
    import os
    if not os.path.exists('data'):
        os.makedirs('data')
    account.save_positions()
    
    print("\n" + "-" * 70)
    print("✅ 激进组合初始建仓完成！")
    print(f"\n📊 持仓市值: ¥{account.get_total_value(prices):,.2f}")
    print(f"💵 可用现金: ¥{account.cash:,.2f}")
    
    print("\n📋 最终持仓:")
    print("-" * 70)
    for code in portfolio.codes:
        if code in account.positions and account.positions[code]['shares'] > 0:
            pos = account.positions[code]
            mv = pos['shares'] * prices[code]
            weight = mv / account.get_total_value(prices) * 100
            print(f"   {portfolio.names[code]:<10} {code}: {pos['shares']}股 @ ¥{pos['avg_cost']:.2f} 市值: ¥{mv:,.2f} ({weight:.1f}%)")

if __name__ == '__main__':
    main()
