# -*- coding: utf-8 -*-
"""
按目前真实持仓跑回测 - 验证指标
起点: config/positions.json (2026-06-24 收盘)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import yaml
import numpy as np
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine, load_klines_from_cache


def main():
    output_lines = []
    def p(msg=''):
        print(msg)
        output_lines.append(msg)

    # ── 1. 加载真实持仓 ──
    with open('config/positions.json', 'r', encoding='utf-8') as f:
        pos_doc = json.load(f)

    positions = pos_doc['positions']
    cash = float(pos_doc['cash'])
    init_total = float(pos_doc['total_value'])
    last_update = pos_doc.get('last_update', '?')
    cur_prices = pos_doc.get('prices', {})

    p('=' * 70)
    p('  按目前真实持仓跑回测 (config/positions.json)')
    p('=' * 70)
    p(f'  持仓快照时间: {last_update}')
    p(f'  持仓标的数: {len([c for c in positions if c != "CASH"])} + CASH')
    p(f'  现金: ¥{cash:>14,.0f}')
    p(f'  持仓市值: ¥{init_total - cash:>14,.0f}')
    p(f'  总值:   ¥{init_total:>14,.0f}')

    # ── 2. 加载 settings + 组合配置 ──
    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)
    with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
        portfolio = yaml.safe_load(f)

    # ── 3. 加载 K 线数据 ──
    klines = load_klines_from_cache(portfolio, 'data/cache', years=5)
    p(f'  加载K线: {len(klines)}/{len(portfolio["assets"])} 只标的')

    # ── 4. 初始化回测引擎 (用真实总值作为初始资金) ──
    engine = BacktestEngine(settings, portfolio, init_total)

    # 注入真实持仓: 写入 portfolio.positions 的 shares
    for code, pos in positions.items():
        if code == 'CASH':
            continue
        if code in engine.portfolio.positions:
            engine.portfolio.positions[code]['shares'] = int(pos.get('shares', 0))
            engine.portfolio.positions[code]['avg_cost'] = float(pos.get('avg_cost', 0))
    engine.portfolio.cash = cash

    p(f'\n  ✅ 真实持仓已注入 PortfolioEngine')

    # ── 5. 跑回测 ──
    result = engine.run(klines)

    if 'error' in result:
        p(f'\n  ❌ 回测失败: {result["error"]}')
        return

    # ── 6. 输出结果 ──
    p('\n' + '=' * 70)
    p('  📊 真实持仓起点回测结果 (5年)')
    p('=' * 70)

    p(f'  初始资金: ¥{result["initial_capital"]:>14,.0f}  (真实持仓总值)')
    p(f'  最终资金: ¥{result["final_capital"]:>14,.0f}')
    p(f'  期间盈亏: ¥{result["final_capital"] - result["initial_capital"]:>+14,.0f}')
    p(f'  总收益率: {result["total_return"]*100:>10.2f}%')
    p('')
    p(f'  年化收益: {result["annual_return"]*100:>10.2f}%   (报告基准 5.24%)')
    p(f'  年化波动: {result["annual_volatility"]*100:>10.2f}%   (报告基准 5.37%)')
    p(f'  最大回撤: {result["max_drawdown"]*100:>10.2f}%   (报告基准 6.99%)')
    p(f'  夏普比率: {result["sharpe_ratio"]:>10.4f}   (报告基准 0.4179)')
    p(f'  日胜率:   {result["win_rate"]*100:>10.2f}%   (报告基准 52.98%)')
    p(f'  交易次数: {result["num_trades"]:>10d}   (报告基准 29)')
    p(f'  回测天数: {result["num_trades"] and result["num_days"] or result["num_days"]}')

    # ── 7. 目标达成情况 ──
    ar_ok = result['annual_return'] >= 0.08
    dd_ok = result['max_drawdown'] <= 0.10
    p('\n' + '-' * 70)
    p('  🎯 目标达成:')
    p(f'     年化收益≥8%:  {"✅ 达标" if ar_ok else "⚠️ 未达标"}  ({result["annual_return"]*100:.2f}%)')
    p(f'     最大回撤≤10%: {"✅ 达标" if dd_ok else "⚠️ 未达标"}  ({result["max_drawdown"]*100:.2f}%)')

    # ── 8. 现金占用分析 ──
    cash_pct = cash / init_total * 100
    p('\n' + '-' * 70)
    p('  💰 现金/仓位分析:')
    p(f'     现金占比:  {cash_pct:.1f}%  (¥{cash:,.0f})')
    p(f'     股票占比:  {100 - cash_pct:.1f}%  (¥{init_total - cash:,.0f})')
    if cash_pct > 30:
        p(f'     ⚠️  现金占比偏高({cash_pct:.1f}%)，拖累年化收益')

    p('\n' + '=' * 70)

    # 写 UTF-8 文件
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'cache', 'check_money_real_result.txt')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    p(f'  结果已写入: {out_path}')


if __name__ == '__main__':
    main()
