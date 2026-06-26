# -*- coding: utf-8 -*-
"""
iFinD MCP实时交易系统
接入同花顺iFinD MCP服务获取实时行情
"""

import os
import sys

# Windows控制台UTF-8编码支持
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import time
import json
import yaml
import requests
import numpy as np
import pandas as pd
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, List, Optional

class IFINDMCPClient:
    def __init__(self):
        self.base_url = "https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-stock-mcp"
        self.auth_token = os.environ.get("IFIND_AUTH_TOKEN", "")
        self.headers = {
            "Authorization": self.auth_token,
            "Content-Type": "application/json"
        }
        if not self.auth_token:
            print("WARNING: IFIND_AUTH_TOKEN not set, iFinD MCP unavailable")
    
    def get_realtime_quote(self, codes: List[str]) -> Optional[Dict]:
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "get_realtime_quote",
                "params": {"codes": codes},
                "id": int(time.time())
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"  ⚠️ iFinD API请求失败: {e}")
            return None
    
    def search_stock(self, query: str) -> Optional[Dict]:
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "search_stock",
                "params": {"query": query},
                "id": int(time.time())
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"  ⚠️ iFinD搜索失败: {e}")
            return None


class IFINDRealTimeTrader:
    def __init__(self):
        with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.cash = 1000000
        self.positions = {}
        self.trade_history = []
        self.equity_curve = []
        self.start_time = None
        self.day_count = 0
        
        print("🔌 初始化iFinD MCP客户端...")
        self.ifind_client = IFINDMCPClient()
        
        self.load_simulation_data()
    
    def load_simulation_data(self):
        print("📥 加载模拟数据作为备用...")
        self.simulation_data = {}
        self.simulation_index = {}
        
        for asset in self.config['assets']:
            code = asset['code']
            filepath = os.path.join('data/cache', f'kline_{code}_daily.parquet')
            if os.path.exists(filepath):
                df = pd.read_parquet(filepath, columns=['close'])
                self.simulation_data[code] = df
                self.simulation_index[code] = 0
                print(f"  ✅ {asset['name']} ({code}) 数据加载完成")
    
    def get_realtime_prices(self) -> Dict[str, float]:
        codes = [asset['code'] for asset in self.config['assets']]
        
        print(f"\n📡 正在从iFinD获取实时行情...")
        result = self.ifind_client.get_realtime_quote(codes)
        
        prices = {}
        
        if result and 'result' in result:
            print(f"  ✅ iFinD实时数据获取成功")
            for item in result.get('result', []):
                code = item.get('code')
                price = item.get('close') or item.get('price')
                if code and price:
                    prices[code] = float(price)
                    print(f"    {code}: ¥{price}")
        else:
            print(f"  ⚠️ iFinD数据获取失败，使用模拟数据")
            prices = self.get_simulation_prices()
        
        return prices
    
    def get_simulation_prices(self) -> Dict[str, float]:
        prices = {}
        for asset in self.config['assets']:
            code = asset['code']
            if code in self.simulation_data:
                df = self.simulation_data[code]
                idx = self.simulation_index[code]
                if idx < len(df):
                    self.simulation_index[code] += 1
                    prices[code] = float(df['close'].iloc[idx])
        return prices
    
    def get_all_prices(self) -> Dict[str, float]:
        return self.get_realtime_prices()
    
    def get_total_value(self, prices: Dict[str, float]) -> float:
        total = self.cash
        for code, pos in self.positions.items():
            if code in prices:
                total += pos['shares'] * prices[code]
        return total
    
    def execute_trade(self, code: str, side: str, shares: int, price: float, commission: float):
        asset_name = next((a['name'] for a in self.config['assets'] if a['code'] == code), code)
        
        if side == 'buy':
            cost = shares * price
            commission_fee = cost * commission
            
            if cost + commission_fee > self.cash:
                print(f"  ❌ [{asset_name}] 资金不足，无法买入")
                return False
            
            self.cash -= cost + commission_fee
            
            if code not in self.positions:
                self.positions[code] = {'shares': 0, 'avg_cost': 0}
            
            old_cost = self.positions[code]['shares'] * self.positions[code]['avg_cost']
            self.positions[code]['shares'] += shares
            self.positions[code]['avg_cost'] = (old_cost + cost) / self.positions[code]['shares']
            
            print(f"  ✅ [{asset_name}] 买入 {shares}股 @ ¥{price:.2f}")
            
        elif side == 'sell':
            if code not in self.positions or self.positions[code]['shares'] < shares:
                print(f"  ❌ [{asset_name}] 持仓不足，无法卖出")
                return False
            
            revenue = shares * price
            commission_fee = revenue * commission
            net_revenue = revenue - commission_fee
            
            self.positions[code]['shares'] -= shares
            if self.positions[code]['shares'] == 0:
                del self.positions[code]
            
            self.cash += net_revenue
            
            print(f"  ✅ [{asset_name}] 卖出 {shares}股 @ ¥{price:.2f}")
        
        self.trade_history.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'code': code,
            'name': asset_name,
            'side': side,
            'shares': shares,
            'price': price,
            'commission': commission_fee
        })
        
        return True
    
    def rebalance(self, prices: Dict[str, float]):
        print("\n📊 开始仓位再平衡...")
        total_value = self.get_total_value(prices)
        print(f"当前账户总值: ¥{total_value:,.2f}")
        
        trades_executed = 0
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
                trades_executed += 1
        
        if trades_executed == 0:
            print("  📊 仓位无需调整")
    
    def print_status(self, prices: Dict[str, float]):
        total_value = self.get_total_value(prices)
        now = datetime.now()
        
        print(f"\n{'='*75}")
        print(f"⏰ {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📈 账户总值: ¥{total_value:,.2f}")
        print(f"💰 可用现金: ¥{self.cash:,.2f}")
        print(f"📊 持仓数量: {len(self.positions)}只")
        print(f"📅 交易天数: {self.day_count}天")
        print(f"{'='*75}")
        
        if self.positions:
            print("\n📋 当前持仓:")
            print(f"{'名称':<10} {'代码':<10} {'持仓':<8} {'现价':<10} {'市值':<14} {'盈亏':<12}")
            print(f"{'-'*75}")
            
            total_market_value = 0
            total_pnl = 0
            
            for asset in self.config['assets']:
                code = asset['code']
                if code in self.positions:
                    shares = self.positions[code]['shares']
                    avg_cost = self.positions[code]['avg_cost']
                    price = prices.get(code, 0)
                    market_value = shares * price
                    pnl = shares * (price - avg_cost)
                    total_market_value += market_value
                    total_pnl += pnl
                    
                    pnl_str = f"+¥{pnl:,.2f}" if pnl >= 0 else f"-¥{abs(pnl):,.2f}"
                    print(f"{asset['name']:<10} {code:<10} {shares:<8} ¥{price:<10.2f} ¥{market_value:<14,.2f} {pnl_str}")
            
            print(f"{'-'*75}")
            pnl_str = f"+¥{total_pnl:,.2f}" if total_pnl >= 0 else f"-¥{abs(total_pnl):,.2f}"
            print(f"{'合计':<20} ¥{total_market_value:<14,.2f} {pnl_str}")
        
        print(f"\n{'='*75}")
    
    def is_market_open(self) -> bool:
        now = datetime.now()
        weekday = now.weekday()
        
        if weekday >= 5:
            return False
        
        current_time = now.time()
        morning_open = dt_time(9, 25)
        morning_close = dt_time(11, 30)
        afternoon_open = dt_time(13, 0)
        afternoon_close = dt_time(15, 0)
        
        return (morning_open <= current_time <= morning_close) or (afternoon_open <= current_time <= afternoon_close)
    
    def wait_until_market_open(self):
        print("\n⏳ 等待开盘...")
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        while True:
            now = datetime.now()
            weekday = now.weekday()
            
            if weekday < 5:
                current_time = now.time()
                morning_open = dt_time(9, 25)
                
                if current_time >= morning_open:
                    break
            
            print(f"  等待交易时段... ({datetime.now().strftime('%H:%M:%S')})")
            time.sleep(60)
    
    def run(self, auto_start: bool = True):
        self.start_time = datetime.now()
        print(f"\n🚀 iFinD MCP实时交易系统启动")
        print(f"📅 {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔌 数据源: 同花顺iFinD MCP")
        print(f"{'='*75}")
        
        if auto_start:
            self.wait_until_market_open()
        
        print("\n🎉 iFinD实时交易已接入！")
        
        while True:
            if not self.is_market_open():
                next_open = self.get_next_market_open()
                print(f"\n⏰ 市场已休市，下个开盘: {next_open}")
                time.sleep(60)
                continue
            
            self.day_count += 1
            print(f"\n{'='*75}")
            print(f"📅 第 {self.day_count} 个交易周期 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*75}")
            
            prices = self.get_all_prices()
            
            if not prices:
                print("\n⚠️ 无法获取行情数据")
                time.sleep(5)
                continue
            
            self.print_status(prices)
            
            if self.day_count == 1 or self.day_count % 15 == 0:
                self.rebalance(prices)
            
            self.equity_curve.append({
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'value': self.get_total_value(prices)
            })
            
            print("\n⏭️ 等待下一个周期(60秒)...")
            time.sleep(60)
    
    def get_next_market_open(self):
        now = datetime.now()
        weekday = now.weekday()
        
        if weekday >= 5:
            days_until_monday = 7 - weekday
            next_day = now + timedelta(days=days_until_monday)
        else:
            current_time = now.time()
            if current_time >= dt_time(15, 0):
                next_day = now + timedelta(days=1)
                if next_day.weekday() >= 5:
                    days_until_monday = 7 - next_day.weekday()
                    next_day = next_day + timedelta(days=days_until_monday)
            else:
                next_day = now
        
        return next_day.replace(hour=9, minute=25, second=0).strftime('%Y-%m-%d %H:%M')
    
    def stop(self):
        print("\n" + "="*75)
        print("📊 iFinD MCP交易结果汇总")
        print("="*75)
        
        if self.equity_curve:
            values = [e['value'] for e in self.equity_curve]
            initial = 1000000
            final = values[-1]
            total_return = (final - initial) / initial
            
            print(f"初始资金: ¥{initial:,.0f}")
            print(f"最终资金: ¥{final:,.0f}")
            print(f"总收益率: {total_return*100:.2f}%")
            print(f"交易次数: {len(self.trade_history)}")
            print(f"持仓数量: {len(self.positions)}只")
        
        print("="*75)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='iFinD MCP实时交易系统')
    parser.add_argument('--auto', action='store_true', help='自动等待开盘时间')
    parser.add_argument('--now', action='store_true', help='立即开始，不等待')
    args = parser.parse_args()
    
    trader = IFINDRealTimeTrader()
    
    try:
        if args.now:
            trader.run(auto_start=False)
        else:
            trader.run(auto_start=args.auto)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断交易")
        trader.stop()


if __name__ == "__main__":
    main()
