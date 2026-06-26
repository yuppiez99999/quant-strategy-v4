#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试优化后的回测引擎"""

from backtest_engine import load_configs, load_klines_from_cache, BacktestEngine

# 加载配置
settings, portfolio = load_configs()

# 加载K线数据
klines = load_klines_from_cache(portfolio, cache_dir='data/cache', years=5)
print(f'✓ 加载 {len(klines)} 个资产的K线数据')

# 运行回测
engine = BacktestEngine(settings, portfolio, initial_capital=1000000)
result = engine.run(klines)

# 显示结果
print('\n' + '='*60)
print('📊 优化后的回测结果 (v5.2 with dynamic weights & adaptive rebalancing)')
print('='*60)
print(f'初始资本:       ¥{result["initial_capital"]:>12,.0f}')
print(f'最终资本:       ¥{result["final_capital"]:>12,.0f}')
print(f'总收益率:       {result["total_return"]*100:>12.2f}%')
print(f'年化收益率:     {result["annual_return"]*100:>12.2f}%  (目标: 8.00%)')
print(f'年化波动率:     {result["annual_volatility"]*100:>12.2f}%')
print(f'夏普比率:       {result["sharpe_ratio"]:>12.4f}')
print(f'最大回撤:       {result["max_drawdown"]*100:>12.2f}%  (限制: 10%)')
print(f'胜率:           {result["win_rate"]*100:>12.2f}%')
print(f'总交易数:       {result["num_trades"]:>12}')
print(f'交易天数:       {result["num_days"]:>12}')

print('\n' + '-'*60)
print('📈 目标检查:')
print('-'*60)
print(f'年化收益 >= 8%:  {result["target_check"]["annual_return_ok"]}')
print(f'最大回撤 <= 10%: {result["target_check"]["max_drawdown_ok"]}')

print('\n💡 对比优化前:')
print(f'  优化前年化收益: 4.00%  →  优化后: {result["annual_return"]*100:.2f}%')
print(f'  改善幅度: +{(result["annual_return"]*100 - 4.00):.2f}% (相对改善 {(result["annual_return"]/0.04 - 1)*100:.1f}%)')
