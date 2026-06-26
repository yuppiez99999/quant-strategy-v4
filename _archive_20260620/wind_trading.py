# -*- coding: utf-8 -*-
"""
Wind API 实时交易系统
目标: 接入 Wind API 获取实时行情
"""

import os
import sys
import time
import yaml
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    import WindPy
    WIND_AVAILABLE = True
except ImportError:
    WIND_AVAILABLE = False
    print("⚠️ WindPy 未安装，使用模拟模式")

class WindClient:
    def __init__(self):
        self.connected = False
        if WIND_AVAILABLE:
            self.connect()
    
    def connect(self):
        try:
            result = WindPy.w.start()
            if result.ErrorCode == 0:
                self.connected = True
                print("✅ Wind API 连接成功")
            else:
                print(f"❌ Wind API 连接失败: {result.ErrorCode}")
        except Exception as e:
            print(f"❌ Wind API 连接异常: {e}")
    
    def get_realtime_quote(self, codes: List[str]) -> Dict[str, Dict]:
        """获取实时行情"""
        quotes = {}
        
        if not self.connected or not WIND_AVAILABLE:
            return self._get_mock_quotes(codes)
        
        try:
            wind_codes = [f"{code}.SH" if code.startswith('6') else f"{code}.SZ" for code in codes]
            result = WindPy.w.wsq(wind_codes, "rt_last,rt_high,rt_low,rt_vol,rt_amt")
            
            if result.ErrorCode == 0:
                for i, code in enumerate(codes):
                    wind_code = wind_codes[i]
                    quotes[code] = {
                        'price': result.Data[0][i] if result.Data[0][i] is not None else 0,
                        'high': result.Data[1][i] if result.Data[1][i] is not None else 0,
                        'low': result.Data[2][i] if result.Data[2][i] is not None else 0,
                        'volume': result.Data[3][i] if result.Data[3][i] is not None else 0,
                        'amount': result.Data[4][i] if result.Data[4][i] is not None else 0,
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
        except Exception as e:
            print(f"❌ 获取行情失败: {e}")
        
        return quotes if quotes else self._get_mock_quotes(codes)
    
    def _get_mock_quotes(self, codes: List[str]) -> Dict[str, Dict]:
        """获取模拟行情"""
        quotes = {}
        for code in codes:
            quotes[code] = {
                'price': 10.0 + (hash(code) % 100) / 10,
                'high': 10.5 + (hash(code) % 100) / 10,
                'low': 9.5 + (hash(code) % 100) / 10,
                'volume': 1000000,
                'amount': 10000000,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_mock': True
            }
        return quotes
    
    def disconnect(self):
        if self.connected and WIND_AVAILABLE:
            WindPy.w.stop()
            self.connected = False


class WindRealTimeTrader:
    def __init__(self):
        self.load_config()
        self.initialize_account()
        self.wind_client = WindClient()
        
        self.last_update = None
        self.last_rebalance = None
        self.rebalance_period = 15
        self.is_running = False
    
    def load_config(self):
        with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        with open('config/settings.yaml', 'r', encoding='utf-8') as f:
            self.settings = yaml.safe_load(f)
        
        self.assets = self.config['assets']
        self.codes = [asset['code'] for asset in self.assets]
        self.names = {asset['code']: asset['name'] for asset in self.assets}
        self.target_weights = {asset['code']: asset['target_weight'] for asset in self.assets}
        self.commissions = {asset['code']: asset['commission'] for asset in self.assets}
    
    def initialize_account(self):
        self.initial_capital = 1000000
        self.cash = self.initial_capital
        self.positions = {}
        self.trade_history = []
        self.equity_curve = []
    
    def get_realtime_prices(self) -> Dict[str, float]:
        """获取实时价格"""
        quotes = self.wind_client.get_realtime_quote(self.codes)
        prices = {code: quote['price'] for code, quote in quotes.items()}
        return prices
    
    def get_total_value(self, prices: Dict[str, float]) -> float:
        """计算账户总价值"""
        total = self.cash
        for code, pos in self.positions.items():
            if code in prices:
                total += pos['shares'] * prices[code]
        return total
    
    def execute_trade(self, code: str, side: str, shares: int, price: float):
        """执行交易"""
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
            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'code': code,
            'name': name,
            'side': side,
            'shares': shares,
            'price': price,
            'commission': commission_fee
        })
        
        return True, result
    
    def rebalance(self, prices: Dict[str, float]):
        """执行再平衡"""
        print(f"\n📊 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 执行再平衡...")
        total_value = self.get_total_value(prices)
        print(f"账户总值: ¥{total_value:,.2f}")
        
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
    
    def print_status(self, prices: Dict[str, float]):
        """打印状态"""
        total_value = self.get_total_value(prices)
        total_return = (total_value - self.initial_capital) / self.initial_capital
        
        print(f"\n{'='*70}")
        print(f"📊 账户状态 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        print(f"💰 初始资金: ¥{self.initial_capital:,.0f}")
        print(f"🎯 当前资金: ¥{total_value:,.0f}")
        print(f"📈 总收益率: {total_return*100:+.2f}%")
        print(f"💵 可用现金: ¥{self.cash:,.2f}")
        print(f"🔄 交易次数: {len(self.trade_history)}")
        print(f"\n📋 持仓明细:")
        print(f"{'名称':<12} {'代码':<10} {'持仓':<8} {'现价':<10} {'市值':<14}")
        print(f"{'-'*70}")
        
        for code in self.codes:
            if code in self.positions:
                shares = self.positions[code]['shares']
                price = prices.get(code, 0)
                market_value = shares * price
                print(f"{self.names[code]:<12} {code:<10} {shares:<8} ¥{price:<10.2f} ¥{market_value:<14,.2f}")
        
        print(f"{'='*70}")
    
    def run(self, interval: int = 60):
        """运行实时交易"""
        print("\n🚀 Wind API 实时交易系统启动")
        print(f"{'='*70}")
        print(f"📊 标的数量: {len(self.codes)}")
        print(f"💰 初始资金: ¥{self.initial_capital:,.0f}")
        print(f"⏱️ 更新间隔: {interval}秒")
        print(f"{'='*70}")
        
        self.is_running = True
        iteration = 0
        
        try:
            while self.is_running:
                iteration += 1
                prices = self.get_realtime_prices()
                
                if iteration == 1:
                    self.rebalance(prices)
                    self.last_rebalance = datetime.now()
                
                if self.last_rebalance and (datetime.now() - self.last_rebalance).days >= self.rebalance_period:
                    self.rebalance(prices)
                    self.last_rebalance = datetime.now()
                
                self.last_update = datetime.now()
                self.equity_curve.append({
                    'datetime': self.last_update,
                    'value': self.get_total_value(prices)
                })
                
                self.print_status(prices)
                
                print(f"\n⏳ 等待 {interval} 秒...")
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n\n⏹️ 用户中断")
        except Exception as e:
            print(f"\n❌ 系统错误: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """停止交易"""
        self.is_running = False
        self.wind_client.disconnect()
        print("\n✅ 系统已停止")


def main():
    trader = WindRealTimeTrader()
    trader.run(interval=60)


if __name__ == "__main__":
    main()
