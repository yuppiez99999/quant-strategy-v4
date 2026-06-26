# -*- coding: utf-8 -*-
"""空仓 100万 + 修复后 portfolio.yaml - 短窗口对比"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml
from backtest_engine import BacktestEngine, load_klines_from_cache


def run(window_days=252, label='1年'):
    out = []
    p = lambda m: (print(m), out.append(m))

    p('=' * 70)
    p(f'  【{label}】空仓100万 + 修复后 portfolio.yaml')
    p('=' * 70)

    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)
    with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
        portfolio = yaml.safe_load(f)

    klines = load_klines_from_cache(portfolio, 'data/cache', years=5)
    p(f'  加载K线: {len(klines)}/{len(portfolio["assets"])}')

    engine = BacktestEngine(settings, portfolio, 1_000_000)
    dates = engine._get_common_dates(klines)
    codes = [a['code'] for a in portfolio.get('assets', []) if a.get('code') and a['code'] != 'CASH']
    price_matrix, all_dates, active_codes = engine._prebuild_price_matrix(klines, codes)

    if price_matrix is not None and len(all_dates) > window_days:
        # 取最近 window 天
        recent_dates = all_dates[-window_days:]
        valid = set(recent_dates)
        dates = all_dates[all_dates.isin(list(valid))]
        if len(dates) > window_days:
            dates = dates[-window_days:]

    last_rebalance = None
    rebalance_freq = 15

    for i, date in enumerate(dates):
        prices = engine._get_day_prices(price_matrix, active_codes, date)
        total_value = engine.portfolio.get_total_value(prices)
        scale = engine._check_drawdown_control(total_value)

        should = False
        if last_rebalance is None:
            should = True
        elif (date - last_rebalance).days >= rebalance_freq:
            should = True
        else:
            cw = engine.portfolio.get_current_weights(prices)
            dw = engine._get_dynamic_weights(klines)
            max_d = max(abs(cw.get(c, 0) - dw.get(c, 0)) for c in dw)
            if max_d > 0.05:
                should = True

        if should:
            tw = engine._get_dynamic_weights(klines)
            allow_c = (last_rebalance is None)
            engine._execute_rebalance(tw, prices, date, scale, allow_cash_rebalance=allow_c)
            last_rebalance = date

        engine.equity_curve.append({'date': str(date), 'value': total_value})

    res = engine._compute_results(dates)
    if 'error' in res:
        p(f'  ❌ {res["error"]}')
        return

    p(f'\n  区间: {dates[0].date()} ~ {dates[-1].date()} ({len(dates)}天)')
    p(f'  初始: ¥{res["initial_capital"]:>12,.0f}')
    p(f'  最终: ¥{res["final_capital"]:>12,.0f}')
    p(f'  收益: {res["total_return"]*100:+.2f}%')
    p(f'  年化: {res["annual_return"]*100:+.2f}%   (报告基准 5.24%)')
    p(f'  波动: {res["annual_volatility"]*100:.2f}%   (报告基准 5.37%)')
    p(f'  回撤: {res["max_drawdown"]*100:.2f}%   (报告基准 6.99%)')
    p(f'  夏普: {res["sharpe_ratio"]:.4f}   (报告基准 0.4179)')
    p(f'  胜率: {res["win_rate"]*100:.2f}%   (报告基准 52.98%)')
    p(f'  交易: {res["num_trades"]} 笔  (报告基准 29)')

    # 各资产年度表现
    p(f'\n  📈 各资产区间内涨跌幅:')
    for code in klines:
        try:
            start = klines[code].loc[:dates[0]].iloc[-1]['close']
            end = klines[code].loc[:dates[-1]].iloc[-1]['close']
            ret = (end / start - 1) * 100
            p(f'     {code}: {ret:+.2f}%')
        except Exception:
            pass

    p('=' * 70)
    out_path = f'data/cache/empty100w_{window_days}d.txt'
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    p(f'  结果: {out_path}')


if __name__ == '__main__':
    run(252, '1年')
    print()
    run(126, '半年')
