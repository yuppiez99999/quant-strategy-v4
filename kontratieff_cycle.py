# -*- coding: utf-8 -*-
"""
康波周期分析与10年收益率预测
基于Kondratieff周期理论的宏观分析
"""

import numpy as np
import pandas as pd
from datetime import datetime
import argparse
import os

CURRENT_YEAR = datetime.now().year

KONDRATIEFF_PHASES = {
    'spring': {'name': '复苏期 (Spring)', 'years': 20, 'stock_return': 0.08, 'bond_return': 0.04, 'commodity_return': 0.03},
    'summer': {'name': '过热期 (Summer)', 'years': 15, 'stock_return': 0.05, 'bond_return': 0.02, 'commodity_return': 0.10},
    'autumn': {'name': '衰退期 (Autumn)', 'years': 10, 'stock_return': 0.00, 'bond_return': 0.06, 'commodity_return': -0.02},
    'winter': {'name': '萧条期 (Winter)', 'years': 15, 'stock_return': 0.02, 'bond_return': 0.05, 'commodity_return': -0.05},
}

CURRENT_PHASE = 'spring'
YEARS_IN_CURRENT_PHASE = CURRENT_YEAR - 2020

def get_kondratieff_cycle(year=CURRENT_YEAR):
    """获取指定年份的康波周期阶段"""
    cycle_length = 60
    years_since_1920 = year - 1920
    position = years_since_1920 % cycle_length
    
    if position < 20:
        return 'spring', position
    elif position < 35:
        return 'summer', position - 20
    elif position < 45:
        return 'autumn', position - 35
    else:
        return 'winter', position - 45

def forecast_next_10_years(initial_capital=1000000, allocation=None):
    """预测未来10年收益率"""
    if allocation is None:
        allocation = {'stocks': 0.50, 'bonds': 0.30, 'commodities': 0.20}
    
    results = []
    capital = initial_capital
    
    for i in range(10):
        year = CURRENT_YEAR + i
        phase, year_in_phase = get_kondratieff_cycle(year)
        phase_data = KONDRATIEFF_PHASES[phase]
        
        stock_ret = phase_data['stock_return']
        bond_ret = phase_data['bond_return']
        commodity_ret = phase_data['commodity_return']
        
        portfolio_return = (
            allocation['stocks'] * stock_ret +
            allocation['bonds'] * bond_ret +
            allocation['commodities'] * commodity_ret
        )
        
        capital = capital * (1 + portfolio_return)
        
        results.append({
            'year': year,
            'phase': phase_data['name'],
            'year_in_phase': year_in_phase + 1,
            'stock_return': stock_ret,
            'bond_return': bond_ret,
            'commodity_return': commodity_ret,
            'portfolio_return': portfolio_return,
            'capital': capital,
            'total_return': (capital - initial_capital) / initial_capital
        })
    
    return results

def print_cycle_overview():
    """打印康波周期概览"""
    print("=" * 60)
    print("          康波周期 (Kondratieff Cycle) 概览")
    print("=" * 60)
    
    cycle_year = CURRENT_YEAR - 1920
    print(f"\n当前年份: {CURRENT_YEAR}")
    print(f"距1920年: {cycle_year} 年")
    print(f"当前周期位置: 第 {cycle_year % 60} 年 (共60年周期)")
    
    phase, year_in_phase = get_kondratieff_cycle()
    phase_data = KONDRATIEFF_PHASES[phase]
    print(f"\n当前阶段: {phase_data['name']}")
    print(f"已持续: {year_in_phase + 1} 年 / {phase_data['years']} 年")
    
    print("\n--- 康波周期四阶段 ---")
    for key, data in KONDRATIEFF_PHASES.items():
        print(f"  {data['name']:20s} 约{data['years']:2d}年")

def print_10year_forecast(results, initial_capital):
    """打印10年预测结果"""
    print("\n" + "=" * 60)
    print("          未来10年组合收益预测")
    print("=" * 60)
    
    print(f"\n初始资金: {initial_capital:,.0f} 元")
    print("资产配置: 股票50%, 债券30%, 商品20%")
    
    print("\n" + "-" * 60)
    print(f"{'年份':>6s} {'阶段':10s} {'阶段年':>5s} {'股票':>6s} {'债券':>6s} {'商品':>6s} {'组合收益':>8s} {'期末资金':>15s}")
    print("-" * 60)
    
    for r in results:
        print(f"{r['year']:6d} {r['phase'][:8]:10s} {r['year_in_phase']:5d} "
              f"{r['stock_return']*100:5.1f}% {r['bond_return']*100:5.1f}% "
              f"{r['commodity_return']*100:5.1f}% {r['portfolio_return']*100:7.1f}% "
              f"{r['capital']:>15,.0f}")
    
    print("-" * 60)
    
    final_capital = results[-1]['capital']
    total_return = (final_capital - initial_capital) / initial_capital * 100
    annualized = (final_capital / initial_capital) ** (1/10) - 1
    
    print(f"\n10年后资金: {final_capital:>15,.0f} 元")
    print(f"累计收益: {total_return:>14.1f} %")
    print(f"年化收益: {annualized*100:>14.1f} %")

def main():
    parser = argparse.ArgumentParser(description='康波周期分析')
    parser.add_argument('--capital', type=float, default=1000000, help='初始资金')
    parser.add_argument('--years', type=int, default=10, help='预测年数')
    args = parser.parse_args()
    
    print_cycle_overview()
    
    results = forecast_next_10_years(initial_capital=args.capital)
    print_10year_forecast(results, args.capital)
    
    print("\n" + "=" * 60)
    print("分析完成。注意: 本分析仅供研究参考，不构成投资建议。")
    print("=" * 60)

if __name__ == '__main__':
    main()
