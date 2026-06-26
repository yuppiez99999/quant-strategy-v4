# -*- coding: utf-8 -*-
"""
实时模拟交易启动器 - 支持定时开盘接入
"""

import os
import sys
import time
import yaml
import numpy as np
import pandas as pd
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, List

class LiveSimulator:
    def __init__(self):
        with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.cash = 1000000
        self.positions = {}
        self.trade_history = []
        self.equity_curve = []
        self.start_time = None
        
        self.load_price_data()
    
    def load_price_data(self):
        self.price_data = {}
        self.price_index = {}
        
        for asset in self.config['assets']:
            code = asset['code']
            filepath = os.path.join('data/cache', f'kline_{code}_daily.parquet')
            if os.path.exists(filepath):
                df = pd.read_parquet(filepath)
                self.price_data[code] = df
                self.price_index[code] = 0
    
    def get_current_price(self, code: str):
        if code not in self.price_data:
            return None
        
        df = self.price_data[code]
        idx = self.price_index[code]
        
        if idx < len(df):
            self.price_index[code] += 1
            return float(df['close'].iloc[idx])
        return None
    
    def get_all_prices(self):
        prices = {}
        for asset in self.config['assets']:
            price = self.get_current_price(asset['code'])
            if price:
                prices[asset['code']] = price
        return prices
    
    def get_total_value(self, prices: Dict[str, float]):
        total = self.cash
        for code, pos in self.positions.items():
            if code in prices:
                total += pos['shares'] * prices[code]
        return total
    
    def execute_trade(self, code: str, side: str, shares: int, price: float, commission: float):
        if side == 'buy':
            cost = shares * price
            commission_fee = cost * commission
            
            if cost + commission_fee > self.cash:
                print(f"  ❌ 资金不足，无法买入 {code}")
                return False
            
            self.cash -= cost + commission_fee
            
            if code not in self.positions:
                self.positions[code] = {'shares': 0, 'avg_cost': 0}
            
            old_cost = self.positions[code]['shares'] * self.positions[code]['avg_cost']
            self.positions[code]['shares'] += shares
            self.positions[code]['avg_cost'] = (old_cost + cost) / self.positions[code]['shares']
            
            print(f"  ✅ 买入 {code}: {shares}股 @ ¥{price:.2f}, 花费 ¥{cost+commission_fee:.2f}")
            
        elif side == 'sell':
            if code not in self.positions or self.positions[code]['shares'] < shares:
                print(f"  ❌ 持仓不足，无法卖出 {code}")
                return False
            
            revenue = shares * price
            commission_fee = revenue * commission
            net_revenue = revenue - commission_fee
            
            self.positions[code]['shares'] -= shares
            if self.positions[code]['shares'] == 0:
                del self.positions[code]
            
            self.cash += net_revenue
            
            print(f"  ✅ 卖出 {code}: {shares}股 @ ¥{price:.2f}, 收入 ¥{net_revenue:.2f}")
        
        self.trade_history.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'code': code,
            'side': side,
            'shares': shares,
            'price': price,
            'commission': commission_fee
        })
        
        return True
    
    def rebalance(self, prices: Dict[str, float]):
        print("\n📊 开始再平衡...")
        total_value = self.get_total_value(prices)
        print(f"当前账户总值: ¥{total_value:,.2f}")
        
        for asset in self.config['assets']:
            code = asset['code']
            target_weight = asset['target_weight']
            commission = asset['commission']
            
            if code not in prices:
                continue
            
            target_amount = total_value * target_weight
            current_shares = self.positions.get(code, {}).get('shares', 0)
            current_amount = current_shares * prices[code]
            
            diff_amount = target_amount - current_amount
            
            if abs(diff_amount) / total_value < 0.02:
                continue
            
            price = prices[code]
            shares = int(abs(diff_amount) / price / 100) * 100
            
            if shares > 0:
                if diff_amount > 0:
                    self.execute_trade(code, 'buy', shares, price, commission)
                else:
                    self.execute_trade(code, 'sell', shares, price, commission)
    
    def print_status(self, prices: Dict[str, float]):
        total_value = self.get_total_value(prices)
        now = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"⏰ {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📈 账户总值: ¥{total_value:,.2f}")
        print(f"💰 可用现金: ¥{self.cash:,.2f}")
        print(f"📊 持仓数量: {len(self.positions)}只")
        
        if self.start_time:
            elapsed = (now - self.start_time).total_seconds() / 3600
            print(f"⏱️ 运行时长: {elapsed:.2f}小时")
        
        print(f"{'='*60}")
        
        if self.positions:
            print("\n📋 当前持仓:")
            print(f"{'股票名称':<12} {'代码':<10} {'持仓':<8} {'现价':<10} {'市值':<12}")
            print(f"{'-'*60}")
            
            total_market_value = 0
            for asset in self.config['assets']:
                code = asset['code']
                if code in self.positions:
                    shares = self.positions[code]['shares']
                    price = prices.get(code, 0)
                    market_value = shares * price
                    total_market_value += market_value
                    print(f"{asset['name']:<12} {code:<10} {shares:<8} ¥{price:<10.2f} ¥{market_value:<12,.2f}")
            
            print(f"{'-'*60}")
            print(f"{'持仓市值合计':<30} ¥{total_market_value:<12,.2f}")
        
        print(f"\n{'='*60}")
    
    def wait_until_market_open(self):
        print("\n⏳ 等待开盘...")
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        while True:
            now = datetime.now()
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            
            if now >= market_open:
                break
            
            wait_seconds = (market_open - now).total_seconds()
            if wait_seconds > 0:
                print(f"  距离开盘还有 {wait_seconds:.0f}秒...")
                time.sleep(min(wait_seconds, 60))
    
    def run(self, auto_start: bool = True):
        self.start_time = datetime.now()
        print(f"\n🚀 实时模拟交易启动")
        print(f"📅 {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        if auto_start:
            self.wait_until_market_open()
        
        print("\n🎉 模拟盘已接入！")
        
        day_count = 0
        while True:
            prices = self.get_all_prices()
            
            if not prices:
                print("\n⚠️ 数据已用完，模拟结束")
                break
            
            day_count += 1
            print(f"\n📅 第 {day_count} 个交易日")
            
            self.print_status(prices)
            
            if day_count == 1 or day_count % 15 == 0:
                self.rebalance(prices)
            
            self.equity_curve.append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'value': self.get_total_value(prices)
            })
            
            print("\n⏭️ 等待下一个交易日...")
            time.sleep(2)
        
        self.print_final_results()
    
    def print_final_results(self):
        print("\n" + "="*60)
        print("📊 模拟交易结果汇总")
        print("="*60)
        
        if self.equity_curve:
            values = [e['value'] for e in self.equity_curve]
            initial = 1000000
            final = values[-1]
            total_return = (final - initial) / initial
            years = len(self.equity_curve) / 252
            annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
            
            print(f"初始资金: ¥{initial:,.0f}")
            print(f"最终资金: ¥{final:,.0f}")
            print(f"总收益率: {total_return*100:.2f}%")
            print(f"年化收益: {annual_return*100:.2f}%")
            print(f"交易次数: {len(self.trade_history)}")
            print(f"持仓数量: {len(self.positions)}只")
        
        print("="*60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='实时模拟交易')
    parser.add_argument('--auto', action='store_true', help='自动等待开盘时间')
    parser.add_argument('--now', action='store_true', help='立即开始，不等待')
    args = parser.parse_args()
    
    simulator = LiveSimulator()
    
    if args.now:
        simulator.run(auto_start=False)
    else:
        simulator.run(auto_start=args.auto)


if __name__ == "__main__":
    main()
