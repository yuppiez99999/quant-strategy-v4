# -*- coding: utf-8 -*-
"""
模拟盘交易系统 - Wind API实时版
功能: 实时行情接入 + 自动交易 + 每日收盘报告 + 策略分析
"""

import os
import sys
import yaml
import subprocess
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
WIND_CLI = os.environ.get(
    "WIND_CLI_PATH",
    os.path.expandvars(r"%USERPROFILE%\.agents\skills\wind-mcp-skill\scripts\cli.mjs")
)

class WindDataProvider:
    @staticmethod
    def get_stock_price(code):
        """获取股票价格，对超时错误自动重试（最多2次，间隔3秒）"""
        windcode = f'{code}.SH' if code.startswith('6') else f'{code}.SZ'
        payload = json.dumps({"windcode": windcode, "indexes": "最新成交价,涨跌幅"})
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                r = subprocess.run(
                    ['node', WIND_CLI, 'call', 'stock_data', 'get_stock_price_indicators', payload],
                    capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30
                )
                if r.stdout:
                    d = json.loads(r.stdout)
                    if d.get('content'):
                        rows = json.loads(d['content'][0]['text'])['data']['rows'][0]
                        return {'price': float(rows[0]), 'change': float(rows[1])}
            except subprocess.TimeoutExpired:
                if attempt < max_retries:
                    time.sleep(3)
                    continue
            except Exception:
                pass
            break
        return {'price': 0, 'change': 0}

    @staticmethod
    def get_fund_price(code):
        """获取基金价格，对超时错误自动重试（最多2次，间隔3秒）"""
        windcode = f'{code}.SH' if code.startswith('5') else f'{code}.SZ'
        payload = json.dumps({"windcode": windcode, "indexes": "最新成交价,涨跌幅"})
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                r = subprocess.run(
                    ['node', WIND_CLI, 'call', 'fund_data', 'get_fund_price_indicators', payload],
                    capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30
                )
                if r.stdout:
                    d = json.loads(r.stdout)
                    if d.get('content'):
                        rows = json.loads(d['content'][0]['text'])['data']['rows'][0]
                        return {'price': float(rows[0]), 'change': float(rows[1])}
            except subprocess.TimeoutExpired:
                if attempt < max_retries:
                    time.sleep(3)
                    continue
            except Exception:
                pass
            break
        return {'price': 0, 'change': 0}

    @staticmethod
    def get_real_time_prices(codes):
        prices = {}
        changes = {}
        for code in codes:
            if code.startswith('5'):
                r = WindDataProvider.get_fund_price(code)
            else:
                r = WindDataProvider.get_stock_price(code)
            prices[code] = r['price']
            changes[code] = r['change']
        return prices, changes

class SimulatedAccount:
    def __init__(self, initial_capital: float = 1000000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        
    def get_total_value(self, prices):
        total = self.cash
        for code, pos in self.positions.items():
            if code in prices:
                total += pos['shares'] * prices[code]
        return total
    
    def buy(self, code, price, shares, commission_rate=0.0005):
        cost = shares * price
        commission = cost * commission_rate
        total_cost = cost + commission
        if total_cost > self.cash:
            return False, "资金不足"
        self.cash -= total_cost
        if code not in self.positions:
            self.positions[code] = {'shares': 0, 'avg_cost': 0}
        old_cost = self.positions[code]['shares'] * self.positions[code]['avg_cost']
        self.positions[code]['shares'] += shares
        self.positions[code]['avg_cost'] = (old_cost + cost) / self.positions[code]['shares']
        return True, "买入成功"

class SimulationEngine:
    def __init__(self, config_path='config/portfolio.yaml', initial_capital=1000000):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.account = SimulatedAccount(initial_capital)
        self.codes = [asset['code'] for asset in self.config['assets']]
        self.names = {asset['code']: asset['name'] for asset in self.config['assets']}
        self.target_weights = {asset['code']: asset['target_weight'] for asset in self.config['assets']}
        
    def run_live_simulation(self):
        print("="*70)
        print("🚀 Wind API 实时模拟交易系统")
        print("="*70)
        
        print(f"\n📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 监控标的: {len(self.codes)} 只")
        print(f"💰 初始资金: ¥{self.account.initial_capital:,.0f}")
        
        print(f"\n⏳ 获取Wind实时行情并初始化持仓...")
        prices, changes = WindDataProvider.get_real_time_prices(self.codes)
        
        for code in self.codes:
            if code in prices and prices[code] > 0:
                target_amount = self.account.initial_capital * self.target_weights[code]
                shares = int(target_amount / prices[code] / 100) * 100
                if shares > 0:
                    self.account.buy(code, prices[code], shares)
        
        self.display_positions(prices, changes)
    
    def display_positions(self, prices, changes):
        total_mv = 0
        total_value = self.account.cash
        
        print(f"\n{'='*70}")
        print("📋 实时持仓")
        print(f"{'='*70}")
        print(f"{'股票名称':<12} {'代码':<10} {'持仓':>6} {'现价':>10} {'涨跌':>8} {'市值':>12} {'权重':>6}")
        print("-"*70)
        
        for code in self.codes:
            if code in self.account.positions:
                pos = self.account.positions[code]
                price = prices.get(code, 0)
                change = changes.get(code, 0)
                mv = pos['shares'] * price
                total_mv += mv
                
                status = "📈" if change >= 0 else "📉"
                weight = (mv / (total_mv + self.account.cash)) * 100
                
                print(f"{status} {self.names[code]:<11} {code:<10} {pos['shares']:>6}  ¥{price:>9.2f}  {change:>+7.2f}%  ¥{mv:>11,.0f}  {weight:>5.1f}%")
        
        total_value = total_mv + self.account.cash
        
        print("-"*70)
        print(f"{'持仓市值':<39} ¥{total_mv:>12,.2f}")
        print(f"{'可用现金':<39} ¥{self.account.cash:>12,.2f}")
        print(f"{'账户总值':<39} ¥{total_value:>12,.2f}")
        print(f"{'='*70}")
        
        self.generate_report(prices, changes, total_value)
    
    def generate_report(self, prices, changes, total_value):
        print("\n� 策略分析")
        print("-"*70)
        
        up_count = sum(1 for c in self.codes if c in changes and changes[c] >= 0)
        down_count = len(self.codes) - up_count
        
        print(f"当日表现: {up_count}只上涨, {down_count}只下跌")
        
        if changes:
            best = max(changes.items(), key=lambda x: x[1])
            worst = min(changes.items(), key=lambda x: x[1])
            print(f"最强: {self.names[best[0]]} (+{best[1]:.2f}%)")
            print(f"最弱: {self.names[worst[0]]} ({worst[1]:.2f}%)")
        
        overweight = []
        underweight = []
        positions = self.account.positions
        
        for code in self.codes:
            if code in positions and code in prices:
                current_w = (positions[code]['shares'] * prices[code]) / total_value * 100
                target_w = self.target_weights[code] * 100
                diff = current_w - target_w
                if diff > 2:
                    overweight.append((self.names[code], diff))
                elif diff < -2:
                    underweight.append((self.names[code], diff))
        
        print("\n🎯 操作建议")
        print("-"*70)
        
        if overweight:
            print("📤 需减仓:")
            for name, diff in overweight:
                print(f"  • {name}: 超配 {diff:.2f}%")
        
        if underweight:
            print("📥 需加仓:")
            for name, diff in underweight:
                print(f"  • {name}: 低配 {abs(diff):.2f}%")
        
        if not overweight and not underweight:
            print("✅ 当前持仓权重正常，无需操作")

if __name__ == "__main__":
    engine = SimulationEngine()
    engine.run_live_simulation()
