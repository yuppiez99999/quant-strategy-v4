# -*- coding: utf-8 -*-
"""
12只标的量化策略 - 主交易程序
目标: 年化≥8%, 回撤≤10%
资金: 100万
"""

import os
import sys
import time
import yaml
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List

class TradingEngine:
    def __init__(self):
        self.load_config()
        self.initialize_account()
        self.load_data()
    
    def load_config(self):
        with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.assets = self.config['assets']
        self.codes = [asset['code'] for asset in self.assets]
        self.names = {asset['code']: asset['name'] for asset in self.assets}
        self.target_weights = {asset['code']: asset['target_weight'] for asset in self.assets}
        self.commissions = {asset['code']: asset['commission'] for asset in self.assets}
    
    def initialize_account(self):
        self.initial_capital = 3000000
        self.cash = self.initial_capital
        self.positions = {}
        self.trade_history = []
        self.equity_curve = []
        self.daily_stats = []
    
    def load_data(self):
        print("📥 加载历史数据...")
        self.price_data = {}
        self.dates = None
        
        for asset in self.assets:
            code = asset['code']
            filepath = os.path.join('data/cache', f'kline_{code}_daily.parquet')
            
            if os.path.exists(filepath):
                df = pd.read_parquet(filepath, columns=['close'])
                df = df.sort_index()
                self.price_data[code] = df
                print(f"  ✅ {asset['name']} ({code}): {len(df)}个交易日")
                
                if self.dates is None:
                    self.dates = df.index.tolist()
                else:
                    common_dates = set(self.dates) & set(df.index.tolist())
                    self.dates = sorted(list(common_dates))
            else:
                print(f"  ❌ {asset['name']} ({code}): 数据文件不存在")
        
        if self.dates:
            print(f"\n📅 共有 {len(self.dates)} 个共同交易日")
            print(f"    起始日期: {self.dates[0].date()}")
            print(f"    结束日期: {self.dates[-1].date()}")
    
    def get_prices_on_date(self, date):
        prices = {}
        for code in self.codes:
            if code in self.price_data and date in self.price_data[code].index:
                prices[code] = float(self.price_data[code].loc[date, 'close'])
        return prices
    
    def get_total_value(self, prices):
        total = self.cash
        for code, pos in self.positions.items():
            if code in prices:
                total += pos['shares'] * prices[code]
        return total
    
    def execute_trade(self, code, side, shares, price):
        name = self.names.get(code, code)
        commission = self.commissions.get(code, 0.0005)
        
        if side == 'buy':
            cost = shares * price
            commission_fee = cost * commission
            total_cost = cost + commission_fee
            
            if total_cost > self.cash:
                return False, f"资金不足"
            
            self.cash -= total_cost
            
            if code not in self.positions:
                self.positions[code] = {'shares': 0, 'avg_cost': 0}
            
            old_cost = self.positions[code]['shares'] * self.positions[code]['avg_cost']
            self.positions[code]['shares'] += shares
            self.positions[code]['avg_cost'] = (old_cost + cost) / self.positions[code]['shares']
            
            result = f"买入 {name} {shares}股 @ ¥{price:.2f}"
        
        else:
            if code not in self.positions or self.positions[code]['shares'] < shares:
                return False, "持仓不足"
            
            revenue = shares * price
            commission_fee = revenue * commission
            net_revenue = revenue - commission_fee
            
            self.positions[code]['shares'] -= shares
            if self.positions[code]['shares'] == 0:
                del self.positions[code]
            
            self.cash += net_revenue
            result = f"卖出 {name} {shares}股 @ ¥{price:.2f}"
        
        self.trade_history.append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'code': code,
            'name': name,
            'side': side,
            'shares': shares,
            'price': price,
            'commission': commission_fee
        })
        
        return True, result
    
    def rebalance(self, prices, date):
        print(f"\n📊 [{date.date()}] 执行再平衡...")
        total_value = self.get_total_value(prices)
        print(f"账户总值: ¥{total_value:,.2f}")
        
        trades = []
        for code in self.codes:
            if code not in prices:
                continue
            
            target_weight = self.target_weights[code]
            target_amount = total_value * target_weight
            
            current_shares = self.positions.get(code, {}).get('shares', 0)
            current_amount = current_shares * prices[code]
            
            diff_amount = target_amount - current_amount
            
            if abs(diff_amount) / total_value < 0.01:
                continue
            
            price = prices[code]
            shares = int(abs(diff_amount) / price / 100) * 100
            
            if shares > 0:
                if diff_amount > 0:
                    success, msg = self.execute_trade(code, 'buy', shares, price)
                else:
                    success, msg = self.execute_trade(code, 'sell', shares, price)
                
                if success:
                    print(f"  ✅ {msg}")
                else:
                    print(f"  ❌ {msg}")
    
    def run_backtest(self):
        print("\n🚀 开始回测...")
        print(f"{'='*70}")
        
        peak_value = self.initial_capital
        max_drawdown = 0
        
        for i, date in enumerate(self.dates):
            prices = self.get_prices_on_date(date)
            
            if not prices:
                continue
            
            total_value = self.get_total_value(prices)
            
            if total_value > peak_value:
                peak_value = total_value
            drawdown = (peak_value - total_value) / peak_value
            if drawdown > max_drawdown:
                max_drawdown = drawdown
            
            self.equity_curve.append({
                'date': date,
                'value': total_value,
                'drawdown': drawdown
            })
            
            if i == 0 or (i + 1) % 15 == 0:
                self.rebalance(prices, date)
            
            if (i + 1) % 50 == 0:
                print(f"⏳ 已完成 {i + 1}/{len(self.dates)} 个交易日")
        
        self.generate_report(max_drawdown)
    
    def generate_report(self, max_drawdown):
        print(f"\n{'='*70}")
        print("📊 回测报告")
        print(f"{'='*70}")
        
        values = [e['value'] for e in self.equity_curve]
        dates = [e['date'] for e in self.equity_curve]
        
        initial = values[0]
        final = values[-1]
        total_return = (final - initial) / initial
        
        years = (dates[-1] - dates[0]).days / 365
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        daily_returns = np.diff(values) / values[:-1]
        annual_volatility = np.std(daily_returns) * np.sqrt(252) if len(daily_returns) > 0 else 0
        sharpe_ratio = (annual_return - 0.03) / annual_volatility if annual_volatility > 0 else 0
        
        print(f"📅 回测周期: {dates[0].date()} - {dates[-1].date()}")
        print(f"💰 初始资金: ¥{initial:,.0f}")
        print(f"🎯 最终资金: ¥{final:,.0f}")
        print(f"📈 总收益率: {total_return*100:.2f}%")
        print(f"📊 年化收益: {annual_return*100:.2f}%")
        print(f"🎲 年化波动: {annual_volatility*100:.2f}%")
        print(f"📉 最大回撤: {max_drawdown*100:.2f}%")
        print(f"⚖️ 夏普比率: {sharpe_ratio:.2f}")
        print(f"🔄 交易次数: {len(self.trade_history)}")
        
        print(f"\n{'='*70}")
        print("📋 最终持仓:")
        print(f"{'名称':<12} {'代码':<10} {'持仓':<8} {'市值':<14}")
        print(f"{'-'*70}")
        
        total_market_value = 0
        for code in self.codes:
            if code in self.positions:
                shares = self.positions[code]['shares']
                price = self.price_data[code].loc[self.dates[-1], 'close']
                market_value = shares * price
                total_market_value += market_value
                print(f"{self.names[code]:<12} {code:<10} {shares:<8} ¥{market_value:<14,.2f}")
        
        print(f"{'-'*70}")
        print(f"{'持仓市值':<22} ¥{total_market_value:<14,.2f}")
        print(f"{'可用现金':<22} ¥{self.cash:<14,.2f}")
        print(f"{'账户总值':<22} ¥{final:<14,.2f}")
        
        print(f"\n{'='*70}")
        print("🎯 目标达成情况:")
        print(f"   年化收益≥8%: {'✅' if annual_return >= 0.08 else '❌'} ({annual_return*100:.2f}%)")
        print(f"   最大回撤≤10%: {'✅' if max_drawdown <= 0.10 else '❌'} ({max_drawdown*100:.2f}%)")
        print(f"{'='*70}")


def main():
    engine = TradingEngine()
    
    if not engine.dates:
        print("❌ 没有可用数据")
        return
    
    engine.run_backtest()


if __name__ == "__main__":
    main()
