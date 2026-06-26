# -*- coding: utf-8 -*-
"""
测试回测 - 验证 OPTIMIZATION_REPORT.md 中的几项指标
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml
from backtest_engine import BacktestEngine, load_klines_from_cache


def main():
    output_lines = []
    def p(msg=''):
        print(msg)
        output_lines.append(msg)

    p('=' * 70)
    p('  验证 OPTIMIZATION_REPORT.md 优化后指标 (backtest_engine.py)')
    p('=' * 70)

    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)

    configs = [
        ('portfolio_v3.yaml', '6标的 v3(报告基准)'),
        ('portfolio.yaml', '24标的 v5.3(当前生产)'),
    ]

    for cfg_name, label in configs:
        with open(f'config/{cfg_name}', 'r', encoding='utf-8') as f:
            portfolio = yaml.safe_load(f)

        klines = load_klines_from_cache(portfolio, 'data/cache', years=5)
        if not klines:
            p(f'\n[{label}] 无数据,跳过')
            continue

        p(f'\n{"="*70}')
        p(f'  配置: {label} ({cfg_name})  标的: {len(klines)}/{len(portfolio["assets"])}')
        p(f'{"="*70}')

        engine = BacktestEngine(settings, portfolio, 1_000_000)
        result = engine.run(klines)

        if 'error' in result:
            p(f'  错误: {result["error"]}')
            continue

        p(f'  初始资金: ¥{result["initial_capital"]:>12,.0f}')
        p(f'  最终资金: ¥{result["final_capital"]:>12,.0f}')
        p(f'  总收益率: {result["total_return"]*100:>10.2f}%')
        p(f'  年化收益: {result["annual_return"]*100:>10.2f}%   (报告基准 5.24%)')
        p(f'  年化波动: {result["annual_volatility"]*100:>10.2f}%   (报告基准 5.37%)')
        p(f'  最大回撤: {result["max_drawdown"]*100:>10.2f}%   (报告基准 6.99%)')
        p(f'  夏普比率: {result["sharpe_ratio"]:>10.4f}   (报告基准 0.4179)')
        p(f'  日胜率:   {result["win_rate"]*100:>10.2f}%   (报告基准 52.98%)')
        p(f'  交易次数: {result["num_trades"]:>10d}   (报告基准 29)')
        p(f'  回测天数: {result["num_days"]:>10d}')

    p(f'\n{"="*70}')
    p('  注: 当前 backtest_engine.py 已是"优化后"版本(动态权重+回撤控制+成本建模)')
    p('  报告中的"优化前"为旧版,需回滚或用对照脚本才能复现')
    p(f'{"="*70}')

    # 写 UTF-8 文件给终端读
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'cache', 'check_money_result.txt')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    p(f'\n  结果已写入: {out_path}')


if __name__ == '__main__':
    main()
