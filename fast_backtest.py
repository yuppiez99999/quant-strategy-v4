# -*- coding: utf-8 -*-
"""
快速回测 - 只回测最近252个交易日
"""

import os
import yaml
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def prebuild_price_matrix(price_data, codes):
    """预建价格矩阵: columns=代码, rows=日期 → O(1) per-date lookup"""
    aligned = {}
    for code in codes:
        if code in price_data:
            aligned[code] = price_data[code]['close']
    if not aligned:
        return None, None, None
    matrix = pd.DataFrame(aligned).sort_index()
    matrix = matrix.ffill()
    return matrix, matrix.index, list(aligned.keys())

def main():
    print("="*70)
    print("12只标的量化策略 - 快速回测 (最近1年)")
    print("="*70)

    with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    assets = config['assets']
    codes = [asset['code'] for asset in assets]
    names = {asset['code']: asset['name'] for asset in assets}
    target_weights = {asset['code']: asset['target_weight'] for asset in assets}

    print(f"\n📊 标的配置: {len(assets)} 只")
    print(f"{'名称':<12} {'代码':<10} {'权重':<8}")
    print("-"*50)
    for asset in assets:
        print(f"{asset['name']:<12} {asset['code']:<10} {asset['target_weight']*100:>5.1f}%")
    print("-"*50)

    print(f"\n📥 加载数据...")
    price_data = {}
    dates = None

    for asset in assets:
        code = asset['code']
        filepath = os.path.join('data/cache', f'kline_{code}_daily.parquet')
        if os.path.exists(filepath):
            df = pd.read_parquet(filepath, columns=['close'])
            df.index = pd.to_datetime(df.index).normalize()
            df = df[~df.index.duplicated(keep='last')]
            price_data[code] = df
            print(f"  ✅ {names[code]} ({code}): {len(df)} 条, {df.index[0].date()} ~ {df.index[-1].date()}")

    if not price_data:
        print("❌ 没有可用数据")
        return

    all_dates = [set(df.index) for df in price_data.values()]
    dates = sorted(list(set.intersection(*all_dates)))
    if len(dates) < 100:
        dates = sorted(list(set.union(*all_dates)))
        print(f"  ⚠️ 共同日期不足，使用所有日期: {dates[0].date()} ~ {dates[-1].date()}")
    dates = dates[-1260:]
    print(f"\n📅 回测区间: {dates[0].date()} ~ {dates[-1].date()}, 共 {len(dates)} 个交易日")

    initial_capital = 3000000
    cash = initial_capital
    positions = {}
    equity_curve = []
    peak_value = initial_capital
    max_drawdown = 0
    trade_count = 0
    last_rebalance = dates[0]

    # 预建价格矩阵 — O(1) per date
    price_matrix, common_dates, active_codes = prebuild_price_matrix(price_data, codes)
    if price_matrix is None or len(common_dates) < 20:
        print("❌ 共同交易日不足")
        return

    # Align dates to common_dates that exist
    common_set = set(common_dates)
    dates = [d for d in dates if d in common_set]
    if len(dates) < 20:
        print("❌ 对齐后日期不足")
        return

    print(f"\n🚀 开始回测...")

    for i, date in enumerate(dates):
        # O(1) single-shot lookup
        if date in price_matrix.index:
            prices_row = price_matrix.loc[date]
        else:
            prev_mask = price_matrix.index <= date
            if not prev_mask.any():
                continue
            prices_row = price_matrix.loc[price_matrix.index[prev_mask][-1]]

        prices = {c: float(prices_row.get(c)) for c in active_codes
                  if prices_row.get(c) and float(prices_row.get(c)) > 0}
        if not prices:
            continue

        total = cash
        for code, pos in positions.items():
            if code in prices:
                total += pos['shares'] * prices[code]

        if total > peak_value:
            peak_value = total
        drawdown = (peak_value - total) / peak_value
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        equity_curve.append({'date': date, 'value': total, 'drawdown': drawdown})

        if i == 0 or (date - last_rebalance).days >= 15:
            for code in active_codes:
                if code not in prices:
                    continue

                target_weight = target_weights[code]
                target_amount = total * target_weight

                current_shares = positions.get(code, {}).get('shares', 0)
                current_amount = current_shares * prices[code]
                diff_amount = target_amount - current_amount

                if abs(diff_amount) / total < 0.02:
                    continue

                price = prices[code]
                shares = int(abs(diff_amount) / price / 100) * 100

                if shares > 0:
                    commission = shares * price * 0.0005
                    if diff_amount > 0:
                        cost = shares * price + commission
                        if cost <= cash:
                            cash -= cost
                            if code not in positions:
                                positions[code] = {'shares': 0, 'avg_cost': 0}
                            old_cost = positions[code]['shares'] * positions[code]['avg_cost']
                            positions[code]['shares'] += shares
                            positions[code]['avg_cost'] = (old_cost + shares * price) / positions[code]['shares']
                            trade_count += 1
                    else:
                        if code in positions and positions[code]['shares'] >= shares:
                            positions[code]['shares'] -= shares
                            if positions[code]['shares'] == 0:
                                del positions[code]
                            cash += shares * price - commission
                            trade_count += 1

            last_rebalance = date

        if (i + 1) % 50 == 0:
            print(f"  ⏳ {i + 1}/{len(dates)} ({total/1e6:.2%})")

    print(f"\n✅ 回测完成!")

    values = [e['value'] for e in equity_curve]
    dates_list = [e['date'] for e in equity_curve]

    initial = values[0]
    final = values[-1]
    total_return = (final - initial) / initial
    years = 1
    annual_return = total_return

    daily_rets = np.diff(values) / values[:-1]
    annual_vol = np.std(daily_rets) * np.sqrt(252) if len(daily_rets) > 0 else 0
    sharpe = (annual_return - 0.03) / annual_vol if annual_vol > 0 else 0

    print(f"\n{'='*70}")
    print("📊 回测结果")
    print(f"{'='*70}")
    print(f"💰 初始资金: ¥{initial:,.0f}")
    print(f"🎯 最终资金: ¥{final:,.0f}")
    print(f"📈 总收益率: {total_return*100:+.2f}%")
    print(f"📊 年化收益: {annual_return*100:+.2f}%")
    print(f"🎲 年化波动: {annual_vol*100:.2f}%")
    print(f"📉 最大回撤: {max_drawdown*100:.2f}%")
    print(f"⚖️ 夏普比率: {sharpe:.2f}")
    print(f"🔄 交易次数: {trade_count}")
    print(f"{'='*70}")

    print(f"\n🎯 目标达成:")
    print(f"   年化≥8%: {'✅' if annual_return >= 0.08 else '❌'} ({annual_return*100:.2f}%)")
    print(f"   回撤≤10%: {'✅' if max_drawdown <= 0.10 else '❌'} ({max_drawdown*100:.2f}%)")

    print(f"\n📋 最终持仓:")
    print(f"{'名称':<12} {'代码':<10} {'持仓':<8} {'市值':<14}")
    print(f"{'-'*70}")

    total_market_value = 0
    last_date = dates_list[-1]
    if last_date in price_matrix.index:
        final_row = price_matrix.loc[last_date]
    else:
        prev_mask = price_matrix.index <= last_date
        final_row = price_matrix.loc[price_matrix.index[prev_mask][-1]] if prev_mask.any() else None

    for code in active_codes:
        if code in positions:
            shares = positions[code]['shares']
            price = float(final_row.get(code, 0)) if final_row is not None else 0
            market_value = shares * price
            total_market_value += market_value
            print(f"{names[code]:<12} {code:<10} {shares:<8} ¥{market_value:<14,.2f}")

    print(f"{'-'*70}")
    total_value = cash + total_market_value
    print(f"{'持仓市值':<22} ¥{total_market_value:<14,.2f}")
    print(f"{'可用现金':<22} ¥{cash:<14,.2f}")
    print(f"{'账户总值':<22} ¥{total_value:<14,.2f}")
    print(f"{'='*70}")

def run_fast_backtest():
    """主系统入口点"""
    main()

if __name__ == "__main__":
    main()
