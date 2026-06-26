# -*- coding: utf-8 -*-
"""买入持有 - 真实持仓 1 年不调仓,作为基准"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json, yaml
from backtest_engine import BacktestEngine, load_klines_from_cache

def buy_and_hold(window_days=252, label='1年'):
    out = []
    p = lambda m: (print(m), out.append(m))
    p('=' * 70)
    p(f'  【{label}买入持有】真实持仓,完全不调仓')
    p('=' * 70)

    with open('config/positions.json', 'r', encoding='utf-8') as f:
        pos_doc = json.load(f)
    positions = pos_doc['positions']
    cash = float(pos_doc['cash'])
    init_total = float(pos_doc['total_value'])
    cur_prices = pos_doc.get('prices', {})

    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)
    with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
        portfolio = yaml.safe_load(f)

    klines = load_klines_from_cache(portfolio, 'data/cache', years=5)
    p(f'  加载K线: {len(klines)}/{len(portfolio["assets"])}')
    p(f'  初始: cash=¥{cash:,.0f} 持仓=¥{init_total-cash:,.0f} 总值=¥{init_total:,.0f}')

    engine = BacktestEngine(settings, portfolio, init_total)
    for code, pos in positions.items():
        if code == 'CASH':
            continue
        if code in engine.portfolio.positions:
            engine.portfolio.positions[code]['shares'] = int(pos.get('shares', 0))
            engine.portfolio.positions[code]['avg_cost'] = float(pos.get('avg_cost', 0))
    engine.portfolio.cash = cash

    # 准备价格矩阵
    dates = engine._get_common_dates(klines)
    codes = [a['code'] for a in portfolio.get('assets', []) if a.get('code') and a['code'] != 'CASH']
    price_matrix, all_dates, active_codes = engine._prebuild_price_matrix(klines, codes)

    if price_matrix is not None and len(all_dates) > window_days:
        recent = all_dates[-window_days:]
        valid = set(recent)
        dates = all_dates[all_dates.isin(list(valid))]
        if len(dates) > window_days:
            dates = dates[-window_days:]

    # ★ 关键: 完全不调仓,只追踪 total_value
    first_value = None
    last_value = None
    start_date = end_date = None
    for i, date in enumerate(dates):
        prices = engine._get_day_prices(price_matrix, active_codes, date)
        total_value = engine.portfolio.get_total_value(prices)
        if i == 0:
            first_value = total_value
            start_date = date
        last_value = total_value
        end_date = date
        engine.equity_curve.append({'date': str(date), 'value': total_value})

    ret = (last_value / first_value - 1) * 100
    p(f'\n  区间: {start_date.date()} ~ {end_date.date()} ({len(dates)}天)')
    p(f'  首日总值: ¥{first_value:,.0f}')
    p(f'  末日总值: ¥{last_value:,.0f}')
    p(f'  收益:    {ret:+.2f}%')
    p(f'  盈亏:    ¥{last_value - first_value:+,.0f}')

    # 实际"按真实持仓 shares"算 - 1年涨幅
    p(f'\n  📈 真实持仓各标的 shares×价格 1年涨跌:')
    for code, pos in positions.items():
        if code == 'CASH':
            continue
        shares = int(pos.get('shares', 0))
        if shares == 0 or code not in klines:
            continue
        try:
            kl = klines[code]
            start_p = float(kl.loc[:start_date].iloc[-1]['close'])
            end_p = float(kl.loc[:end_date].iloc[-1]['close'])
            cur_p = float(cur_prices.get(code, end_p))
            chg = (end_p / start_p - 1) * 100
            mv_start = shares * start_p
            mv_end = shares * end_p
            pnl = mv_end - mv_start
            p(f'     {code}: {shares:>8d}股 ¥{start_p:.2f}→¥{end_p:.2f} ({chg:+.2f}%) 盈亏¥{pnl:+,.0f}  持仓¥{shares*cur_p:,.0f}')
        except Exception as e:
            p(f'     {code}: 错误 {e}')

    p('=' * 70)
    out_path = f'data/cache/buy_hold_{window_days}d.txt'
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))


if __name__ == '__main__':
    buy_and_hold(252, '1年')
    print()
    buy_and_hold(126, '半年')
