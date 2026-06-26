# -*- coding: utf-8 -*-
"""
按目前真实持仓跑 1 年回测 (最近 252 个交易日)
验证 CASH 调仓在 2025-2026 区间的实际效果
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


def run_short_window(window_days: int = 252, label: str = '1年'):
    output_lines = []
    def p(msg=''):
        print(msg)
        output_lines.append(msg)

    p('=' * 70)
    p(f'  按目前真实持仓跑 {label} 回测 (最近 {window_days} 个交易日)')
    p('=' * 70)

    # ── 1. 加载真实持仓 ──
    with open('config/positions.json', 'r', encoding='utf-8') as f:
        pos_doc = json.load(f)
    positions = pos_doc['positions']
    cash = float(pos_doc['cash'])
    init_total = float(pos_doc['total_value'])
    last_update = pos_doc.get('last_update', '?')
    cur_prices = pos_doc.get('prices', {})

    p(f'  持仓快照: {last_update}')
    p(f'  标的: {len([c for c in positions if c != "CASH"])} + CASH')
    p(f'  现金: ¥{cash:,.0f}  持仓市值: ¥{init_total - cash:,.0f}  总值: ¥{init_total:,.0f}')

    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)
    with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
        portfolio = yaml.safe_load(f)

    klines = load_klines_from_cache(portfolio, 'data/cache', years=5)
    p(f'  加载K线: {len(klines)}/{len(portfolio["assets"])} 只标的')

    # ── 2. 初始化引擎 + 注入真实持仓 ──
    engine = BacktestEngine(settings, portfolio, init_total)
    for code, pos in positions.items():
        if code == 'CASH':
            continue
        if code in engine.portfolio.positions:
            engine.portfolio.positions[code]['shares'] = int(pos.get('shares', 0))
            engine.portfolio.positions[code]['avg_cost'] = float(pos.get('avg_cost', 0))
    engine.portfolio.cash = cash

    # ── 3. 重写 run():强制 window ──
    dates = engine._get_common_dates(klines)
    if len(dates) < 20:
        p('  ❌ 数据不足')
        return

    codes = [a['code'] for a in portfolio.get('assets', []) if a.get('code') and a['code'] != 'CASH']
    price_matrix, all_dates, active_codes = engine._prebuild_price_matrix(klines, codes)

    if price_matrix is not None:
        valid_set = set(dates)
        dates = all_dates[all_dates.isin([d for d in all_dates if d in valid_set])]
        # ★ 关键: 强制取最近 window_days 个交易日
        if len(dates) > window_days:
            dates = dates[-window_days:]
        if len(dates) < 20:
            p('  ❌ 窗口数据不足')
            return

    last_rebalance = None
    rebalance_frequency = 15

    for i, date in enumerate(dates):
        prices = engine._get_day_prices(price_matrix, active_codes, date)
        total_value = engine.portfolio.get_total_value(prices)
        position_scale = engine._check_drawdown_control(total_value)

        should_rebalance = False
        if last_rebalance is None:
            should_rebalance = True
        elif (date - last_rebalance).days >= rebalance_frequency:
            should_rebalance = True
        else:
            current_weights = engine.portfolio.get_current_weights(prices)
            dynamic_weights = engine._get_dynamic_weights(klines, lookback=20)
            max_drift = max(abs(current_weights.get(code, 0) - dynamic_weights.get(code, 0))
                           for code in dynamic_weights)
            if max_drift > 0.05:
                should_rebalance = True

        if should_rebalance:
            target_weights = engine._get_dynamic_weights(klines, lookback=20)
            allow_cash = (last_rebalance is None)
            engine._execute_rebalance(target_weights, prices, date, position_scale,
                                     allow_cash_rebalance=allow_cash)
            last_rebalance = date

        engine.equity_curve.append({'date': str(date), 'value': total_value})

    result = engine._compute_results(dates)

    if 'error' in result:
        p(f'  ❌ {result["error"]}')
        return

    # ── 4. 输出 ──
    p(f'\n  回测区间: {dates[0].date()} ~ {dates[-1].date()} ({len(dates)} 个交易日, {len(dates)/252:.2f} 年)')
    p('\n' + '=' * 70)
    p(f'  📊 {label}真实持仓回测结果')
    p('=' * 70)

    p(f'  初始资金: ¥{result["initial_capital"]:>14,.0f}')
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

    ar_ok = result['annual_return'] >= 0.08
    dd_ok = result['max_drawdown'] <= 0.10
    p('\n  🎯 目标达成:')
    p(f'     年化≥8%:  {"✅" if ar_ok else "⚠️"}  ({result["annual_return"]*100:.2f}%)')
    p(f'     回撤≤10%: {"✅" if dd_ok else "⚠️"}  ({result["max_drawdown"]*100:.2f}%)')

    # 交易分布
    initial_cash_trades = [t for t in engine.trades if t.get('reason') == 'INITIAL_CASH_REBALANCE']
    rebalance_trades = [t for t in engine.trades if t.get('reason') != 'INITIAL_CASH_REBALANCE']
    p('\n  📋 交易分布:')
    p(f'     首日 CASH 调仓: {len(initial_cash_trades)} 笔  (释放多余现金到目标比例)')
    p(f'     后续权重调仓:   {len(rebalance_trades)} 笔')
    if initial_cash_trades:
        total_buy = sum(t['amount'] for t in initial_cash_trades)
        p(f'     CASH 调仓买入总额: ¥{total_buy:,.0f}')
        # 列出被买入的标的
        by_code = {}
        for t in initial_cash_trades:
            by_code[t['code']] = by_code.get(t['code'], 0) + t['amount']
        p(f'     买入标的:')
        for code, amt in sorted(by_code.items(), key=lambda x: -x[1])[:10]:
            p(f'       {code}: ¥{amt:,.0f}')

    p('\n' + '=' * 70)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'cache', f'check_money_{window_days}d_result.txt')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    p(f'  结果已写入: {out_path}')


if __name__ == '__main__':
    # 跑两个窗口: 1 年 + 半年
    run_short_window(252, '1年')
    print()
    run_short_window(126, '半年')
