# -*- coding: utf-8 -*-
"""
实时模拟交易系统 - 使用本地数据模拟实时行情
iFinD MCP连接备用方案
"""

import os
import sys
import io
import time
import yaml
import numpy as np
import pandas as pd
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, List, Optional

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

class LocalDataTrader:
    def __init__(self):
        with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.cash = 1000000
        self.positions = {}
        self.trade_history = []
        self.equity_curve = []
        self.start_time = None
        self.day_count = 0
        self.current_data_index = 0

        print(" 加载本地数据作为实时行情源...")
        self.load_local_data()

    def load_local_data(self):
        self.stock_data = {}
        self.data_index = {}

        for asset in self.config['assets']:
            code = asset['code']
            filepath = os.path.join('data/cache', f'kline_{code}_daily.parquet')
            if os.path.exists(filepath):
                df = pd.read_parquet(filepath, columns=['close'])
                self.stock_data[code] = df
                self.data_index[code] = 0
                print(f"  ✅ {asset['name']} ({code}): {len(df)}条数据")
            else:
                print(f"  ⚠️ {asset['name']} ({code}): 无本地数据")

    def get_current_prices(self) -> Dict[str, float]:
        prices = {}

        for asset in self.config['assets']:
            code = asset['code']
            if code in self.stock_data:
                df = self.stock_data[code]
                idx = self.data_index[code]

                if idx < len(df):
                    row = df.iloc[idx]
                    prices[code] = float(row['close'])
                    self.data_index[code] += 1

        return prices

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
                print(f"  ❌ [{asset_name}] 资金不足")
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
                print(f"  ❌ [{asset_name}] 持仓不足")
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
        print("\n 仓位再平衡...")
        total_value = self.get_total_value(prices)
        print(f"账户总值: ¥{total_value:,.2f}")

        for asset in self.config['assets']:
            code = asset['code']
            target_weight = asset['target_weight']
            commission = asset.get('commission', 0.0005)  # 默认佣金0.05%

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

        print(f"\n{'='*70}")
        print(f"⏰ {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f" 账户总值: ¥{total_value:,.2f}")
        print(f" 可用现金: ¥{self.cash:,.2f}")
        print(f" 持仓数量: {len(self.positions)}只")
        print(f" 交易天数: {self.day_count}天")
        print(f"{'='*70}")

        if self.positions:
            print("\n 当前持仓:")
            print(f"{'名称':<10} {'代码':<10} {'持仓':<8} {'现价':<10} {'市值':<14} {'盈亏':<12}")
            print(f"{'-'*70}")

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

            print(f"{'-'*70}")
            pnl_str = f"+¥{total_pnl:,.2f}" if total_pnl >= 0 else f"-¥{abs(total_pnl):,.2f}"
            print(f"{'合计':<20} ¥{total_market_value:<14,.2f} {pnl_str}")

        print(f"\n{'='*70}")

    def run_simulation(self):
        self.start_time = datetime.now()
        print(f"\n 模拟实时交易系统启动")
        print(f" {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f" 数据源: 本地历史数据模拟")
        print(f"{'='*70}")

        while True:
            self.day_count += 1
            print(f"\n{'='*70}")
            print(f" 第 {self.day_count} 个交易日 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}")

            prices = self.get_current_prices()

            if not prices:
                print("\n⚠️ 数据已用完，模拟结束")
                break

            self.print_status(prices)

            if self.day_count == 1 or self.day_count % 15 == 0:
                self.rebalance(prices)

            self.equity_curve.append({
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'value': self.get_total_value(prices)
            })

            print("\n⏭️ 下一个交易日(按Enter跳过)...")
            try:
                input()
            except:
                break

        self.print_final_results()

    def print_final_results(self):
        print("\n" + "="*70)
        print(" 模拟交易结果汇总")
        print("="*70)

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

        print("="*70)


def main():
    trader = LocalDataTrader()
    trader.run_simulation()


if __name__ == "__main__":
    main()
